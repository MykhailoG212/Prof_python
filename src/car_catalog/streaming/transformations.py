"""Lazy-перетворення потокових записів."""

import csv
from collections.abc import Iterable, Iterator
from io import StringIO

from car_catalog.streaming.models import CarRecord, CarSummary


def summarize_cars(cars: Iterable[CarRecord]) -> Iterator[CarSummary]:
    """Створює короткі звіти про автомобілі, коли їх запитує споживач."""
    return (
        CarSummary(car.id, car.full_name, car.year, car.price)
        for car in cars
    )


def format_car_rows(cars: Iterable[CarRecord]) -> Iterator[str]:
    """Формує CSV-подібні рядки експорту без проміжного списку."""
    for car in cars:
        buffer = StringIO()
        csv.writer(buffer, lineterminator="").writerow(
            (car.id, car.brand, car.model, car.year, f"{car.price:.2f}", car.mileage)
        )
        yield buffer.getvalue()
