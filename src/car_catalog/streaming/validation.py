"""Перевірка та типізація рядків каталогу."""

import math
from collections.abc import Iterable, Iterator

from car_catalog.streaming.models import CarRecord, ValidationStats
from car_catalog.streaming.parsers import CsvRow

_REQUIRED_FIELDS = ("id", "brand", "model", "year", "price", "mileage")


class _InvalidCarRow(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_car_rows(
    rows: Iterable[CsvRow],
    stats: ValidationStats | None = None,
) -> Iterator[CarRecord]:
    """Видає валідні записи, підраховуючи кожен відхилений рядок і причину."""
    for row in rows:
        try:
            if None in row:
                raise _InvalidCarRow("unexpected extra fields")
            values: dict[str, str] = {}
            for field in _REQUIRED_FIELDS:
                value = row.get(field)
                if not isinstance(value, str):
                    raise _InvalidCarRow(f"missing {field}")
                values[field] = value.strip()

            try:
                car_id = int(values["id"])
            except ValueError as error:
                raise _InvalidCarRow("invalid id") from error
            brand = values["brand"]
            model = values["model"]
            try:
                year = int(values["year"])
            except ValueError as error:
                raise _InvalidCarRow("invalid year") from error
            try:
                price = float(values["price"])
            except ValueError as error:
                raise _InvalidCarRow("invalid price") from error
            try:
                mileage = int(values["mileage"])
            except ValueError as error:
                raise _InvalidCarRow("invalid mileage") from error

            if car_id < 1:
                raise _InvalidCarRow("id must be positive")
            if not brand or not model:
                raise _InvalidCarRow("brand and model must be non-empty")
            if year < 1886:
                raise _InvalidCarRow("year must be at least 1886")
            if not math.isfinite(price) or price < 0:
                raise _InvalidCarRow("price must be finite and non-negative")
            if mileage < 0:
                raise _InvalidCarRow("mileage must be non-negative")
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            if stats is not None:
                stats.invalid_count += 1
                reason = error.reason if isinstance(error, _InvalidCarRow) else type(error).__name__
                stats.invalid_reasons[reason] += 1
            continue

        if stats is not None:
            stats.valid_count += 1
        yield CarRecord(car_id, brand, model, year, price, mileage)
