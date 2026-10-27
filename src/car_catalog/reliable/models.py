"""Моделі конфігурації та даних на межі введення-виведення."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class Vehicle:
    vehicle_id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    minimum_year: int
    maximum_year: int
    minimum_price: float
    maximum_price: float
    invalid_record_policy: Literal["strict", "tolerant"]


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str
    path: Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    input_path: Path
    output_path: Path
    processing: ProcessingConfig
    logging: LoggingConfig
