import pytest

from car_catalog.models import Car
from car_catalog.services import (
    calculate_average_price,
    filter_by_make,
    filter_by_year,
    find_lowest_mileage_car,
    find_most_expensive_car,
)


@pytest.fixture
def sample_cars() -> list[Car]:
    return [
        Car("Tesla", "Model Y", 2023, 50000.0, 20000),
        Car("BMW", "M3", 2021, 70000.0, 30000),
        Car("Tesla", "Model 3", 2021, 35000.0, 45000),
    ]


def test_filter_by_make(sample_cars: list[Car]) -> None:
    result = filter_by_make(sample_cars, "Tesla")
    assert len(result) == 2


def test_filter_by_year(sample_cars: list[Car]) -> None:
    result = filter_by_year(sample_cars, 2021)
    assert len(result) == 2


def test_find_most_expensive_car(sample_cars: list[Car]) -> None:
    car = find_most_expensive_car(sample_cars)
    assert car is not None
    assert car.price == 70000.0


def test_find_lowest_mileage_car(sample_cars: list[Car]) -> None:
    car = find_lowest_mileage_car(sample_cars)
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
