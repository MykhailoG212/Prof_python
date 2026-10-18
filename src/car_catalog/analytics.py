"""Функціональні фільтри та агрегування даних каталогу."""

from collections.abc import Callable
from typing import Any

from car_catalog.decorators import measure_time
from car_catalog.models import Car


def create_price_range_filter(
    min_price: float,
    max_price: float,
) -> Callable[[Car], bool]:
    """Створює closure-предикат для фільтрації за включним діапазоном цін."""
    if min_price > max_price:
        raise ValueError("Мінімальна ціна не може перевищувати максимальну.")

    def predicate(car: Car) -> bool:
        return min_price <= car.price <= max_price

    return predicate


def create_min_year_filter(min_year: int) -> Callable[[Car], bool]:
    """Створює closure-предикат для фільтрації за мінімальним роком."""

    def predicate(car: Car) -> bool:
        return car.year >= min_year

    return predicate


def filter_cars(
    cars: list[Car],
    predicate: Callable[[Car], bool],
) -> list[Car]:
    """Фільтрує автомобілі за переданою функцією-предикатом."""
    return [car for car in cars if predicate(car)]


def sort_cars_by_price(
    cars: list[Car],
    descending: bool = False,
) -> list[Car]:
    """Повертає автомобілі, відсортовані за ціною lambda-ключем."""
    return sorted(cars, key=lambda car: car.price, reverse=descending)


def calculate_variadic_average(*prices: float) -> float:
    """Обчислює середнє значення довільної кількості цін."""
    if not prices:
        return 0.0
    return sum(prices) / len(prices)


def create_car_record(**fields: Any) -> Car:
    """Створює автомобіль із keyword-полів; ``make`` підтримується як alias."""
    allowed_fields = {"brand", "make", "model", "year", "price", "mileage"}
    unexpected_fields = fields.keys() - allowed_fields
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise TypeError(f"Невідомі поля автомобіля: {names}")
    if "brand" in fields and "make" in fields:
        raise TypeError("Вкажіть лише одне з полів: brand або make.")

    return Car(
        brand=str(fields.get("brand", fields.get("make", "Unknown"))),
        model=str(fields.get("model", "Unknown")),
        year=int(fields.get("year", 2000)),
        price=float(fields.get("price", 0.0)),
        mileage=int(fields.get("mileage", 0)),
    )


def find_most_expensive_car(cars: list[Car]) -> Car | None:
    """Повертає найдорожчий автомобіль або None для порожнього списку."""
    return max(cars, key=lambda car: car.price, default=None)


@measure_time
def calculate_total_and_average_price(cars: list[Car]) -> tuple[float, float]:
    """Обчислює сумарну та середню ціну без створення проміжного списку."""
    if not cars:
        return 0.0, 0.0
    total = sum(car.price for car in cars)
    return total, total / len(cars)
