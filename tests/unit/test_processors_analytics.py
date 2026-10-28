"""Тести структур даних та аналітичних функцій ЛР2."""

from collections import deque
from inspect import signature

import pytest

from car_catalog.analytics import (
    calculate_total_and_average_price,
    calculate_variadic_average,
    create_car_record,
    create_min_year_filter,
    create_price_range_filter,
    filter_cars,
    find_most_expensive_car,
    sort_cars_by_price,
)
from car_catalog.benchmark import benchmark_lookup, generate_dataset
from car_catalog.decorators import measure_time, repeat
from car_catalog.main import run_lab2_demo
from car_catalog.models import Car
from car_catalog.processors import (
    build_cars_by_id_index,
    count_cars_by_brand,
    extract_cars_brief_tuples,
    get_unique_brands,
    group_cars_by_brand,
)


@pytest.fixture
def cars() -> list[Car]:
    return [
        Car("Tesla", "Model Y", 2023, 50_000.0, 20_000),
        Car("BMW", "M3", 2021, 70_000.0, 30_000),
        Car("Tesla", "Model 3", 2021, 35_000.0, 45_000),
    ]


def test_processors_cover_collection_operations(cars: list[Car]) -> None:
    assert get_unique_brands(cars) == {"Tesla", "BMW"}
    assert build_cars_by_id_index(cars) == {1: cars[0], 2: cars[1], 3: cars[2]}
    assert count_cars_by_brand(cars) == {"Tesla": 2, "BMW": 1}
    assert group_cars_by_brand(cars) == {"Tesla": [cars[0], cars[2]], "BMW": [cars[1]]}
    assert extract_cars_brief_tuples(cars) == [
        ("Tesla", "Model Y", 2023),
        ("BMW", "M3", 2021),
        ("Tesla", "Model 3", 2021),
    ]


def test_processors_handle_empty_catalog() -> None:
    assert get_unique_brands([]) == set()
    assert build_cars_by_id_index([]) == {}
    assert not count_cars_by_brand([])
    assert group_cars_by_brand([]) == {}
    assert extract_cars_brief_tuples([]) == []


def test_closure_filters_and_universal_filter(cars: list[Car]) -> None:
    in_price_range = create_price_range_filter(35_000.0, 50_000.0)
    from_2022 = create_min_year_filter(2022)

    assert filter_cars(cars, in_price_range) == [cars[0], cars[2]]
    assert filter_cars(cars, from_2022) == [cars[0]]
    with pytest.raises(ValueError, match="Мінімальна ціна"):
        create_price_range_filter(10_000.0, 1_000.0)


def test_sorting_and_aggregations(cars: list[Car], capsys: pytest.CaptureFixture[str]) -> None:
    assert sort_cars_by_price(cars) == [cars[2], cars[0], cars[1]]
    assert sort_cars_by_price(cars, descending=True) == [cars[1], cars[0], cars[2]]
    assert find_most_expensive_car(cars) is cars[1]
    assert find_most_expensive_car([]) is None
    assert calculate_variadic_average(10.0, 20.0, 30.0) == 20.0
    assert calculate_variadic_average() == 0.0
    assert calculate_total_and_average_price(cars) == pytest.approx((155_000.0, 155_000.0 / 3))
    assert calculate_total_and_average_price([]) == (0.0, 0.0)
    assert "[BENCHMARK]" in capsys.readouterr().out


def test_create_car_record_accepts_brand_and_make_alias() -> None:
    expected = Car("Audi", "A6", 2020, 30_000.0, 10_000)
    assert create_car_record(
        brand="Audi", model="A6", year=2020, price=30_000, mileage=10_000
    ) == expected
    assert create_car_record(
        make="Audi", model="A6", year=2020, price=30_000, mileage=10_000
    ) == expected
    assert create_car_record() == Car("Unknown", "Unknown", 2000, 0.0, 0)


def test_create_car_record_rejects_ambiguous_or_unknown_fields() -> None:
    with pytest.raises(TypeError, match="brand або make"):
        create_car_record(brand="Audi", make="Audi")
    with pytest.raises(TypeError, match="Невідомі поля"):
        create_car_record(color="red")


def test_repeat_runs_function_and_preserves_metadata() -> None:
    calls: list[tuple[int, str]] = []

    @repeat(3)
    def record_call(value: int, *, label: str) -> int:
        calls.append((value, label))
        return len(calls)

    assert record_call(7, label="car") == 3
    assert calls == [(7, "car")] * 3
    assert str(signature(record_call)) == "(value: int, *, label: str) -> int"
    with pytest.raises(ValueError, match="не меншою за 1"):
        repeat(0)


def test_measure_time_preserves_return_and_reports_elapsed(capsys: pytest.CaptureFixture[str]) -> None:
    @measure_time
    def add(left: int, right: int) -> int:
        return left + right

    assert add(2, 3) == 5
    assert "add виконано за " in capsys.readouterr().out


def test_benchmark_lookup_and_dataset_validation() -> None:
    cars = generate_dataset(3)
    assert len(cars) == 3
    assert benchmark_lookup(3)[0] >= 0
    assert benchmark_lookup(3)[1] >= 0
    with pytest.raises(ValueError, match="додатним"):
        generate_dataset(0)


def test_lab2_demo_records_history(cars: list[Car], capsys: pytest.CaptureFixture[str]) -> None:
    history: deque[str] = deque(["Переглянуто каталог"], maxlen=3)
    run_lab2_demo(cars, history)

    output = capsys.readouterr().out
    assert "[set comprehension]" in output
    assert "[Counter]" in output
    assert "[deque]" in output
    assert history[-1] == "Виконано демонстрацію ЛР2"
