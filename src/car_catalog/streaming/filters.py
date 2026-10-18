"""Lazy-фільтрація записів каталогу."""

from collections.abc import Iterable, Iterator
from itertools import islice

from car_catalog.streaming.models import CarRecord


def filter_cars(
    cars: Iterable[CarRecord],
    brand: str | None = None,
    year: int | None = None,
) -> Iterator[CarRecord]:
    """Фільтрує за маркою без урахування регістру та/або точним роком."""
    normalized_brand = brand.strip().casefold() if brand is not None else None
    for car in cars:
        if normalized_brand is not None and car.brand.casefold() != normalized_brand:
            continue
        if year is not None and car.year != year:
            continue
        yield car


def first_matching_cars(
    cars: Iterable[CarRecord],
    limit: int,
    brand: str | None = None,
    year: int | None = None,
) -> Iterator[CarRecord]:
    """Повертає не більше перших N збігів і припиняє читання достроково."""
    if limit < 0:
        raise ValueError("Ліміт має бути невід'ємним.")
    return islice(filter_cars(cars, brand=brand, year=year), limit)


def find_car_by_id(cars: Iterable[CarRecord], car_id: int) -> CarRecord | None:
    """Знаходить запис за ID, завершуючи читання відразу після збігу."""
    return next((car for car in cars if car.id == car_id), None)
