"""Unit-тести компонентів потокової обробки та ітераторів ЛР3."""

from pathlib import Path

import pytest

from car_catalog.streaming.analytics import calculate_statistics
from car_catalog.streaming.batches import batched, flatten_batches
from car_catalog.streaming.benchmark import write_synthetic_dataset
from car_catalog.streaming.filters import first_matching_cars
from car_catalog.streaming.iterators import (
    CarIdIterator,
    first_car_ids,
    flatten_nested,
    infinite_car_ids,
)
from car_catalog.streaming.models import CarRecord, ValidationStats
from car_catalog.streaming.parsers import CsvRow
from car_catalog.streaming.transformations import format_car_rows, summarize_cars
from car_catalog.streaming.validation import validate_car_rows


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


def test_first_matching_cars_stops_after_requested_match_count() -> None:
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


def test_empty_catalog_statistics() -> None:
    stats = calculate_statistics([])
    assert stats.count == 0
    assert stats.average_price == 0.0
    assert stats.most_expensive is None
    assert stats.lowest_mileage is None
    assert stats.brand_counts == {}


def test_synthetic_dataset_argument_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="від'ємним"):
        write_synthetic_dataset(tmp_path / "data.csv", -1)
    with pytest.raises(ValueError, match="Інтервал"):
        write_synthetic_dataset(tmp_path / "data.csv", 1, invalid_every=-1)
