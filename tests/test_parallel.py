"""Перевірки оптимізованої аналітики, конкурентності та кешу ЛР9."""

import json
from pathlib import Path

import pytest

from car_catalog.analytics import (
    AnalyticsResult,
    BenchmarkCar,
    CachedCarAnalytics,
    analyze_cars,
    analyze_cars_numpy,
    generate_dataset,
)
from car_catalog.parallel import (
    analyze_cars_with_processes,
    analyze_cars_with_threads,
    demonstrate_race_condition,
    load_catalog_files,
)
from car_catalog.profiling_tools import measure_memory, profile_function


def _assert_equivalent(expected: AnalyticsResult, actual: AnalyticsResult) -> None:
    assert expected.count == actual.count
    assert expected.minimum_mileage == actual.minimum_mileage
    assert expected.maximum_mileage == actual.maximum_mileage
    assert expected.brand_counts == actual.brand_counts
    assert expected.average_price == pytest.approx(actual.average_price)
    assert expected.price_variance == pytest.approx(actual.price_variance)
    assert expected.price_standard_deviation == pytest.approx(actual.price_standard_deviation)
    assert expected.average_score == pytest.approx(actual.average_score)


@pytest.mark.parametrize("size", (0, 1, 120))
def test_baseline_numpy_and_parallel_analytics_are_equivalent(size: int) -> None:
    cars = generate_dataset(size)
    baseline = analyze_cars(cars)
    _assert_equivalent(baseline, analyze_cars_numpy(cars))
    _assert_equivalent(baseline, analyze_cars_with_threads(cars, workers=4))
    _assert_equivalent(baseline, analyze_cars_with_processes(cars, workers=2))


def test_generated_dataset_is_reproducible_and_has_vin() -> None:
    first = generate_dataset(20, seed=7)
    second = generate_dataset(20, seed=7)

    assert first == second
    assert all(len(car.vin) == 17 for car in first)


def test_lock_prevents_lost_counter_updates() -> None:
    result = demonstrate_race_condition(iterations=200, workers=8)

    assert result.expected == 1_600
    assert result.synchronized == result.expected
    assert result.unsynchronized < result.expected


def test_cached_brand_statistics_are_reused_and_invalidated() -> None:
    cars = generate_dataset(24)
    cached = CachedCarAnalytics(cars)
    first = cached.statistics_for_brand(cars[0].brand)
    second = cached.statistics_for_brand(cars[0].brand)

    assert first is second
    assert cached.statistics_for_brand.cache_info().hits >= 1

    updated = cars + [
        BenchmarkCar(
            brand=cars[0].brand,
            model="New",
            year=2025,
            price=1_000.0,
            mileage=1,
            vin="VIN0000000000000",
        )
    ]
    cached.replace_cars(updated)
    refreshed = cached.statistics_for_brand(cars[0].brand)

    assert refreshed is not first
    assert refreshed.count == first.count + 1
    assert refreshed.average_price != first.average_price


def test_threaded_loader_parses_json_and_csv_in_input_order(tmp_path: Path) -> None:
    json_file = tmp_path / "cars.json"
    json_file.write_text(
        json.dumps(
            [
                {
                    "brand": "Toyota",
                    "model": "Camry",
                    "year": 2020,
                    "price": 25_000,
                    "mileage": 45_000,
                    "vin": "JSONVIN000000000",
                }
            ]
        ),
        encoding="utf-8",
    )
    csv_file = tmp_path / "cars.csv"
    csv_file.write_text(
        "brand,model,year,price,mileage\nHonda,Civic,2021,27000,32000\n",
        encoding="utf-8",
    )

    cars = load_catalog_files((json_file, csv_file), workers=2)

    assert [(car.brand, car.model) for car in cars] == [
        ("Toyota", "Camry"),
        ("Honda", "Civic"),
    ]
    assert cars[1].vin.startswith("FILE")


def test_loader_surfaces_invalid_input(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"unexpected": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="JSON"):
        load_catalog_files((invalid,))


def test_profile_and_memory_helpers_return_results_and_metrics() -> None:
    cars = generate_dataset(10)

    result, report = profile_function(analyze_cars, cars, top_n=5)
    memory_result, memory = measure_memory(analyze_cars, cars)

    assert result.count == 10
    assert report.entries
    assert "ncalls" in report.formatted_output
    assert memory_result == result
    assert memory.current_bytes >= 0
    assert memory.peak_bytes >= memory.current_bytes
