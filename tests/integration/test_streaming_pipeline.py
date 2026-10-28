"""Integration-тести файлового streaming pipeline ЛР3."""

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
from car_catalog.streaming.benchmark import compare_processing, write_synthetic_dataset
from car_catalog.streaming.filters import find_car_by_id
from car_catalog.streaming.models import CarRecord, ValidationStats
from car_catalog.streaming.parsers import parse_csv_rows
from car_catalog.streaming.pipeline import build_pipeline, iter_car_records
from car_catalog.streaming.readers import clean_lines, read_lines
from car_catalog.streaming.validation import validate_car_rows

pytestmark = pytest.mark.integration


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


def test_streaming_reader_cleaner_parser_and_validation(csv_path: Path) -> None:
    stats = ValidationStats()
    rows = parse_csv_rows(clean_lines(read_lines(csv_path)))
    cars = list(validate_car_rows(rows, stats))

    assert [car.id for car in cars] == [1, 2, 3]
    assert stats.valid_count == 3
    assert stats.invalid_count == 2
    assert stats.invalid_reasons["invalid id"] == 1
    assert stats.invalid_reasons["brand and model must be non-empty"] == 1


def test_pipeline_filters_records_and_stops_at_requested_match(csv_path: Path) -> None:
    stats = ValidationStats()
    cars = build_pipeline([csv_path], brand="tesla", year=2021, stats=stats)

    assert list(cars) == [
        CarRecord(3, "Tesla", "Model 3", 2021, 35_000.0, 45_000)
    ]
    assert stats.valid_count == 3
    assert stats.invalid_count == 2


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


def test_generated_dataset_matches_eager_and_streaming_results(tmp_path: Path) -> None:
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
