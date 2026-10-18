"""Потокова агрегація та операції itertools над записами автомобілів."""

from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import accumulate, groupby, pairwise

from car_catalog.streaming.models import CarRecord, CarStatistics


def streaming_average(values: Iterable[float]) -> float:
    """Обчислює середнє за один прохід із O(1) пам'яттю."""
    total = 0.0
    count = 0
    for value in values:
        total += value
        count += 1
    return total / count if count else 0.0


def calculate_statistics(cars: Iterable[CarRecord]) -> CarStatistics:
    """Обчислює лічильник, середню ціну, min/max і марки за один прохід."""
    count = 0
    total_price = 0.0
    most_expensive: CarRecord | None = None
    lowest_mileage: CarRecord | None = None
    brand_counts: Counter[str] = Counter()

    for count, car in enumerate(cars, start=1):
        total_price += car.price
        brand_counts[car.brand] += 1
        if most_expensive is None or car.price > most_expensive.price:
            most_expensive = car
        if lowest_mileage is None or car.mileage < lowest_mileage.mileage:
            lowest_mileage = car

    return CarStatistics(
        count=count,
        average_price=total_price / count if count else 0.0,
        most_expensive=most_expensive,
        lowest_mileage=lowest_mileage,
        brand_counts=dict(brand_counts),
    )


def running_total_prices(cars: Iterable[CarRecord]) -> Iterator[float]:
    """Видає накопичувальну суму цін через itertools.accumulate."""
    return accumulate(car.price for car in cars)


def consecutive_price_changes(
    cars: Iterable[CarRecord],
) -> Iterator[tuple[float, float]]:
    """Видає пари послідовних цін для аналізу змін через itertools.pairwise."""
    prices = (car.price for car in cars)
    return pairwise(prices)


def group_cars_by_brand(
    cars: Iterable[CarRecord],
) -> Iterator[tuple[str, list[CarRecord]]]:
    """Сортує записи за маркою та групує сусідні записи через itertools.groupby."""
    ordered_cars = sorted(cars, key=lambda car: car.brand.casefold())
    for brand, group in groupby(ordered_cars, key=lambda car: car.brand):
        yield brand, list(group)
