import pytest

from car_catalog.models import Car
from car_catalog.services import (
    calculate_average_price,
    filter_by_year,
    find_by_brand,
    find_lowest_mileage,
    find_most_expensive,
)


@pytest.fixture
def sample_cars() -> list[Car]:
    return [
        Car("Tesla", "Model Y", 2023, 50000.0, 20000),
        Car("BMW", "M3", 2021, 70000.0, 30000),
        Car("Tesla", "Model 3", 2021, 35000.0, 45000),
    ]


def test_filter_by_make(sample_cars: list[Car]) -> None:
    result = find_by_brand(sample_cars, " tEsLa ")
    assert len(result) == 2


def test_filter_by_year(sample_cars: list[Car]) -> None:
    result = filter_by_year(sample_cars, 2021)
    assert len(result) == 2


def test_find_most_expensive_car(sample_cars: list[Car]) -> None:
    car = find_most_expensive(sample_cars)
    assert car is not None
    assert car.price == 70000.0


def test_find_lowest_mileage_car(sample_cars: list[Car]) -> None:
    car = find_lowest_mileage(sample_cars)
    assert car is not None
    assert car.mileage == 20000


def test_calculate_average_price(sample_cars: list[Car]) -> None:
    assert calculate_average_price(sample_cars) == pytest.approx(51666.67, 0.01)


def test_car_validation() -> None:
    with pytest.raises(ValueError):
        Car("Test", "Fail", 1800, 100.0, 10)
    with pytest.raises(ValueError):
        Car("Test", "Fail", 2020, -1.0, 10)
    with pytest.raises(ValueError):
        Car("Test", "Fail", 2020, 100.0, -1)
    with pytest.raises(ValueError):
        Car(" ", "Fail", 2020, 100.0, 1)
    with pytest.raises(ValueError):
        Car("Test", " ", 2020, 100.0, 1)
    with pytest.raises(ValueError):
        Car("Test", "Fail", 2020, float("nan"), 1)


def test_empty_catalog_results() -> None:
    assert find_most_expensive([]) is None
    assert find_lowest_mileage([]) is None
    assert calculate_average_price([]) == 0.0
