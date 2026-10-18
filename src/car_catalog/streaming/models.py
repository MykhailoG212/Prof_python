"""Типи записів і результатів потокового каталогу."""

from collections import Counter
from dataclasses import dataclass, field
from typing import NamedTuple


class CarRecord(NamedTuple):
    """Перевірений запис автомобіля з CSV-файлу."""

    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"


class CarSummary(NamedTuple):
    """Коротке представлення автомобіля для потокового експорту."""

    id: int
    name: str
    year: int
    price: float


@dataclass(slots=True)
class ValidationStats:
    """Кількість коректних і відхилених CSV-записів."""

    valid_count: int = 0
    invalid_count: int = 0
    invalid_reasons: Counter[str] = field(default_factory=Counter)


@dataclass(frozen=True, slots=True)
class CarStatistics:
    """Агрегована статистика, побудована одним проходом потоку."""

    count: int
    average_price: float
    most_expensive: CarRecord | None
    lowest_mileage: CarRecord | None
    brand_counts: dict[str, int]
