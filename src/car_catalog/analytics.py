"""Фільтри та продуктивна аналітика каталогу автомобілів."""

import math
import random
from collections.abc import Callable, Sequence
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from typing import Protocol

import numpy as np

from car_catalog.decorators import measure_time
from car_catalog.models import Car


class CarData(Protocol):
    """Мінімальний інтерфейс автомобіля для аналітичних функцій."""

    @property
    def brand(self) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError

    @property
    def year(self) -> int:
        raise NotImplementedError

    @property
    def price(self) -> float:
        raise NotImplementedError

    @property
    def mileage(self) -> int:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class BenchmarkCar:
    """Незмінний запис синтетичного набору даних для ЛР9."""

    brand: str
    model: str
    year: int
    price: float
    mileage: int
    vin: str


@dataclass(frozen=True, slots=True)
class AnalyticsResult:
    """Зведена статистика каталогу; дисперсія розраховується для всієї популяції."""

    count: int
    average_price: float
    minimum_mileage: int
    maximum_mileage: int
    price_variance: float
    price_standard_deviation: float
    average_score: float
    brand_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class BrandStatistics:
    """Статистика автомобілів одного виробника."""

    brand: str
    count: int
    average_price: float
    minimum_mileage: int
    maximum_mileage: int
    price_variance: float
    price_standard_deviation: float
    average_score: float


def generate_dataset(size: int, seed: int = 42) -> list[BenchmarkCar]:
    """Створює відтворюваний набір синтетичних автомобілів заданого розміру."""
    if size < 0:
        raise ValueError("Розмір набору даних не може бути від'ємним.")

    generator = random.Random(seed)
    brands = ("Toyota", "Honda", "Ford", "BMW", "Audi", "Volvo", "Hyundai", "Kia")
    models = ("A1", "Civic", "Focus", "Model S", "Corolla", "XC60", "Elantra", "Sportage")
    return [
        BenchmarkCar(
            brand=brands[index % len(brands)],
            model=models[index % len(models)],
            year=generator.randint(2000, 2025),
            price=round(generator.uniform(8_000.0, 120_000.0), 2),
            mileage=generator.randint(0, 300_000),
            vin=f"VIN{index:014d}",
        )
        for index in range(size)
    ]


def car_score(car: CarData) -> float:
    """Обчислює рейтинг цінності: новіші, дешевші авто з меншим пробігом вище."""
    return 1_000.0 - car.price / 100.0 - car.mileage / 1_000.0 + (car.year - 2000) * 2.0


def _empty_result() -> AnalyticsResult:
    return AnalyticsResult(0, 0.0, 0, 0, 0.0, 0.0, 0.0, {})


def analyze_cars(cars: Sequence[CarData]) -> AnalyticsResult:
    """Обчислює всі показники одним проходом Python і другим проходом дисперсію."""
    if not cars:
        return _empty_result()

    prices_total = 0.0
    scores_total = 0.0
    minimum_mileage = cars[0].mileage
    maximum_mileage = cars[0].mileage
    brand_counts: Counter[str] = Counter()
    for car in cars:
        prices_total += car.price
        scores_total += car_score(car)
        minimum_mileage = min(minimum_mileage, car.mileage)
        maximum_mileage = max(maximum_mileage, car.mileage)
        brand_counts[car.brand] += 1

    count = len(cars)
    average_price = prices_total / count
    squared_deviation_total = 0.0
    for car in cars:
        squared_deviation_total += (car.price - average_price) ** 2
    variance = squared_deviation_total / count
    return AnalyticsResult(
        count=count,
        average_price=average_price,
        minimum_mileage=minimum_mileage,
        maximum_mileage=maximum_mileage,
        price_variance=variance,
        price_standard_deviation=math.sqrt(variance),
        average_score=scores_total / count,
        brand_counts=dict(brand_counts),
    )


def analyze_cars_numpy(cars: Sequence[CarData]) -> AnalyticsResult:
    """Векторизовано обчислює числові показники NumPy."""
    if not cars:
        return _empty_result()

    prices = np.fromiter((car.price for car in cars), dtype=np.float64, count=len(cars))
    mileages = np.fromiter((car.mileage for car in cars), dtype=np.int64, count=len(cars))
    years = np.fromiter((car.year for car in cars), dtype=np.float64, count=len(cars))
    scores = 1_000.0 - prices / 100.0 - mileages / 1_000.0 + (years - 2000.0) * 2.0
    brand_counts = Counter(car.brand for car in cars)
    variance = float(np.var(prices))
    return AnalyticsResult(
        count=len(cars),
        average_price=float(np.mean(prices)),
        minimum_mileage=int(np.min(mileages)),
        maximum_mileage=int(np.max(mileages)),
        price_variance=variance,
        price_standard_deviation=math.sqrt(variance),
        average_score=float(np.mean(scores)),
        brand_counts=dict(brand_counts),
    )


def merge_analytics_results(results: list[AnalyticsResult]) -> AnalyticsResult:
    """Об'єднує незалежні часткові статистики без втрати точності дисперсії."""
    nonempty = [result for result in results if result.count]
    if not nonempty:
        return _empty_result()

    count = sum(result.count for result in nonempty)
    average_price = sum(result.average_price * result.count for result in nonempty) / count
    variance_total = sum(
        result.count
        * (result.price_variance + (result.average_price - average_price) ** 2)
        for result in nonempty
    )
    brand_counts: Counter[str] = Counter()
    for result in nonempty:
        brand_counts.update(result.brand_counts)
    variance = variance_total / count
    return AnalyticsResult(
        count=count,
        average_price=average_price,
        minimum_mileage=min(result.minimum_mileage for result in nonempty),
        maximum_mileage=max(result.maximum_mileage for result in nonempty),
        price_variance=variance,
        price_standard_deviation=math.sqrt(variance),
        average_score=sum(result.average_score * result.count for result in nonempty) / count,
        brand_counts=dict(brand_counts),
    )


def calculate_brand_statistics(cars: Sequence[CarData], brand: str) -> BrandStatistics:
    """Обчислює статистику вибраного виробника."""
    selected = tuple(car for car in cars if car.brand == brand)
    result = analyze_cars(selected)
    return BrandStatistics(
        brand=brand,
        count=result.count,
        average_price=result.average_price,
        minimum_mileage=result.minimum_mileage,
        maximum_mileage=result.maximum_mileage,
        price_variance=result.price_variance,
        price_standard_deviation=result.price_standard_deviation,
        average_score=result.average_score,
    )


class CachedCarAnalytics:
    """Кеш статистики виробників із явною інвалідацією при заміні каталогу."""

    def __init__(self, cars: Sequence[CarData]) -> None:
        self._cars = tuple(cars)

    @lru_cache(maxsize=256)
    def statistics_for_brand(self, brand: str) -> BrandStatistics:
        """Повертає кешовану статистику; кеш-ключ містить екземпляр і марку."""
        return calculate_brand_statistics(self._cars, brand)

    def replace_cars(self, cars: Sequence[CarData]) -> None:
        """Атомарно замінює snapshot даних та очищає кеш методу."""
        self._cars = tuple(cars)
        self.statistics_for_brand.cache_clear()


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
