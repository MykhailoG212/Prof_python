"""Тести потокового каталогу та ітераторів лабораторної роботи №3."""

import csv
from pathlib import Path

import pytest

from car_catalog.streaming.analytics import (
    calculate_statistics,
    consecutive_price_changes,
    group_cars_by_brand,
    running_total_prices,
    streaming_average,
)
from car_catalog.streaming.batches import batched, flatten_batches
from car_catalog.streaming.benchmark import (
    compare_processing,
    write_synthetic_dataset,
)
from car_catalog.streaming.filters import (
    filter_cars,
    find_car_by_id,
    first_matching_cars,
)
from car_catalog.streaming.iterators import (
    CarIdIterator,
    first_car_ids,
    flatten_nested,
    infinite_car_ids,
)
from car_catalog.streaming.models import CarRecord, ValidationStats
from car_catalog.streaming.parsers import CsvRow, parse_csv_rows
from car_catalog.streaming.pipeline import build_pipeline, iter_car_records
from car_catalog.streaming.readers import clean_lines, read_lines
from car_catalog.streaming.transformations import format_car_rows, summarize_cars
from car_catalog.streaming.validation import validate_car_rows


def write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("id", "brand", "model", "year", "price", "mileage"))
        writer.writerows(rows)


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "cars.csv"
    write_csv(
        path,
        [
            [1, "Tesla", "Model Y", 2023, 50_000, 20_000],
            [2, "BMW", "M3", 2021, 70_000, 30_000],
            [3, "Tesla", "Model 3", 2021, 35_000, 45_000],
            ["bad", "Broken", "Car", 2020, "NaN", -1],
            [4, "Toyota", "", 2020, 25_000, 10_000],
        ],
    )
    return path


def test_custom_iterator_and_bounded_infinite_generator() -> None:
    iterator = CarIdIterator(3, 6)
    assert iter(iterator) is iterator
    assert list(iterator) == [3, 4, 5]
    assert list(iterator) == []
    assert list(first_car_ids(4, 10)) == [10, 11, 12, 13]
    assert list(first_car_ids(5)) == list(range(1, 6))
    assert next(infinite_car_ids(7)) == 7
    with pytest.raises(ValueError, match="додатним"):
        CarIdIterator(0)
    with pytest.raises(ValueError, match="невід'ємним"):
        list(first_car_ids(-1))


def test_recursive_yield_from_flatten() -> None:
    assert list(flatten_nested([1, [2, (3, 4)], 5])) == [1, 2, 3, 4, 5]


def test_streaming_reader_cleaner_parser_and_validation(csv_path: Path) -> None:
    stats = ValidationStats()
    lines = clean_lines(read_lines(csv_path))
    rows = parse_csv_rows(lines)
    cars = list(validate_car_rows(rows, stats))

    assert [car.id for car in cars] == [1, 2, 3]
    assert stats.valid_count == 3
    assert stats.invalid_count == 2
    assert stats.invalid_reasons["invalid id"] == 1
    assert stats.invalid_reasons["brand and model must be non-empty"] == 1


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ({"id": "bad", "brand": "A", "model": "B", "year": "2020", "price": "1", "mileage": "0"}, "invalid id"),
        ({"id": "0", "brand": "A", "model": "B", "year": "2020", "price": "1", "mileage": "0"}, "id must be positive"),
        ({"id": "1", "brand": "", "model": "B", "year": "2020", "price": "1", "mileage": "0"}, "brand and model must be non-empty"),
        ({"id": "1", "brand": "A", "model": "B", "year": "1885", "price": "1", "mileage": "0"}, "year must be at least 1886"),
        ({"id": "1", "brand": "A", "model": "B", "year": "2020", "price": "inf", "mileage": "0"}, "price must be finite and non-negative"),
        ({"id": "1", "brand": "A", "model": "B", "year": "2020", "price": "-1", "mileage": "0"}, "price must be finite and non-negative"),
        ({"id": "1", "brand": "A", "model": "B", "year": "2020", "price": "1", "mileage": "-1"}, "mileage must be non-negative"),
        ({"id": "1", "brand": "A", "model": "B", "year": "2020", "price": "1"}, "missing mileage"),
        ({"id": "1", "brand": "A", "model": "B", "year": "2020", "price": "1", "mileage": "0", None: ["extra"]}, "unexpected extra fields"),
    ],
)
def test_validation_rejects_invalid_rows(
    row: CsvRow,
    reason: str,
) -> None:
    stats = ValidationStats()

    assert list(validate_car_rows([row], stats)) == []
    assert stats.valid_count == 0
    assert stats.invalid_count == 1
    assert stats.invalid_reasons[reason] == 1


def test_pipeline_filters_first_n_and_stops_early(csv_path: Path) -> None:
    stats = ValidationStats()
    cars = build_pipeline([csv_path], brand="tesla", year=2021, stats=stats)
    assert list(cars) == [
        CarRecord(3, "Tesla", "Model 3", 2021, 35_000.0, 45_000)
    ]
    assert stats.valid_count == 3
    assert stats.invalid_count == 2

    consumed: list[int] = []

    def source():
        for number in range(10):
            consumed.append(number)
            yield CarRecord(number + 1, "A", str(number), 2020, 1.0, number)

    first_two = list(first_matching_cars(source(), 2, brand="A"))
    assert [car.id for car in first_two] == [1, 2]
    assert consumed == [0, 1]
    with pytest.raises(ValueError, match="невід'ємним"):
        list(first_matching_cars([], -1))


def test_iter_car_records_chains_multiple_csv_files(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    write_csv(first, [[1, "Tesla", "Y", 2023, 1, 0]])
    write_csv(second, [[2, "BMW", "M3", 2022, 2, 1]])

    assert [car.id for car in iter_car_records([first, second])] == [1, 2]


def test_find_by_id_terminates_at_first_match(csv_path: Path) -> None:
    stats = ValidationStats()
    found = find_car_by_id(iter_car_records([csv_path], stats), 2)

    assert found is not None
    assert found.model == "M3"
    assert stats.valid_count == 2
    assert stats.invalid_count == 0


def test_batches_flatten_transformations_and_validation() -> None:
    values = list(range(7))
    batches = list(batched(iter(values), 3))
    assert batches == [[0, 1, 2], [3, 4, 5], [6]]
    assert list(flatten_batches(batches)) == values
    assert list(batched([], 2)) == []
    with pytest.raises(ValueError, match="не меншим за 1"):
        list(batched([], 0))

    car = CarRecord(1, "Tesla", "Model Y", 2023, 50_000.0, 20_000)
    assert list(summarize_cars([car]))[0].name == "Tesla Model Y"
    assert list(format_car_rows([car])) == ["1,Tesla,Model Y,2023,50000.00,20000"]
    quoted_car = CarRecord(2, "A,B", "Model", 2023, 1.0, 0)
    assert list(format_car_rows([quoted_car])) == ['2,"A,B",Model,2023,1.00,0']


def test_streaming_aggregations_and_itertools(csv_path: Path) -> None:
    cars = list(iter_car_records([csv_path]))
    stats = calculate_statistics(cars)
    assert stats.count == 3
    assert stats.average_price == pytest.approx(155_000 / 3)
    assert stats.most_expensive == cars[1]
    assert stats.lowest_mileage == cars[0]
    assert stats.brand_counts == {"Tesla": 2, "BMW": 1}
    assert list(running_total_prices(cars)) == [50_000.0, 120_000.0, 155_000.0]
    assert list(consecutive_price_changes(cars)) == [
        (50_000.0, 70_000.0),
        (70_000.0, 35_000.0),
    ]
    assert [(brand, len(group)) for brand, group in group_cars_by_brand(cars)] == [
        ("BMW", 1),
        ("Tesla", 2),
    ]
    assert streaming_average(car.price for car in cars) == pytest.approx(155_000 / 3)
    assert streaming_average(iter(())) == 0.0


def test_empty_catalog_statistics() -> None:
    stats = calculate_statistics([])
    assert stats.count == 0
    assert stats.average_price == 0.0
    assert stats.most_expensive is None
    assert stats.lowest_mileage is None
    assert stats.brand_counts == {}


def test_generated_dataset_and_eager_lazy_100k_comparison(tmp_path: Path) -> None:
    path = tmp_path / "large-cars.csv"
    write_synthetic_dataset(path, 100_000, invalid_every=10_000)
    eager, lazy = compare_processing(path)

    assert eager.statistics.count == lazy.statistics.count == 100_000
    assert eager.validation.invalid_count == lazy.validation.invalid_count == 10
    assert eager.statistics == lazy.statistics
    assert eager.peak_memory_bytes > lazy.peak_memory_bytes
    assert eager.elapsed_seconds > 0
    assert lazy.elapsed_seconds > 0
    assert eager.time_to_first_record_seconds > 0
    assert lazy.time_to_first_record_seconds > 0


def test_synthetic_dataset_argument_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="від'ємним"):
        write_synthetic_dataset(tmp_path / "data.csv", -1)
    with pytest.raises(ValueError, match="Інтервал"):
        write_synthetic_dataset(tmp_path / "data.csv", 1, invalid_every=-1)
