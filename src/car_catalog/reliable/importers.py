"""Потоковий CSV-імпорт із чіткими помилками валідації."""

import csv
import math
from collections.abc import Iterator, Mapping
from pathlib import Path

from car_catalog.reliable.exceptions import DataImportError, RecordValidationError
from car_catalog.reliable.models import ProcessingConfig, Vehicle

_FIELDS = ("vehicle_id", "brand", "model", "year", "price", "mileage")


def parse_vehicle(row: Mapping[str, str | None], line_number: int, config: ProcessingConfig) -> Vehicle:
    """Перетворює CSV-рядок на Vehicle, зберігаючи першопричину через chaining."""
    try:
        values = {name: (row[name] or "").strip() for name in _FIELDS}
    except KeyError as error:
        raise RecordValidationError("missing required column", line_number=line_number) from error
    try:
        vehicle_id = int(values["vehicle_id"])
        year = int(values["year"])
        price = float(values["price"])
        mileage = int(values["mileage"])
    except ValueError as error:
        raise RecordValidationError("numeric field has invalid value", line_number=line_number) from error
    if vehicle_id <= 0:
        raise RecordValidationError("vehicle_id must be positive", line_number=line_number, field="vehicle_id")
    if not values["brand"] or not values["model"]:
        raise RecordValidationError("brand and model must be non-empty", line_number=line_number)
    if not config.minimum_year <= year <= config.maximum_year:
        raise RecordValidationError("year is outside configured range", line_number=line_number, field="year")
    if price < 0:
        raise RecordValidationError("price must be non-negative", line_number=line_number, field="price")
    if not math.isfinite(price) or not config.minimum_price <= price <= config.maximum_price:
        raise RecordValidationError("price is outside configured range", line_number=line_number, field="price")
    if mileage < 0:
        raise RecordValidationError("mileage must be non-negative", line_number=line_number, field="mileage")
    return Vehicle(vehicle_id, values["brand"], values["model"], year, price, mileage)


def read_vehicles(path: Path, config: ProcessingConfig) -> Iterator[tuple[int, Vehicle | RecordValidationError]]:
    """Читає CSV рядок за рядком, тому файл не накопичується в пам'яті."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            if header is None:
                raise DataImportError("CSV has no required header")
            fieldnames = [name.strip() for name in header]
            if len(fieldnames) != len(set(fieldnames)):
                raise DataImportError("CSV header contains duplicate columns")
            missing = set(_FIELDS) - set(fieldnames)
            unexpected = set(fieldnames) - set(_FIELDS)
            if missing or unexpected:
                details = []
                if missing:
                    details.append(f"missing: {', '.join(sorted(missing))}")
                if unexpected:
                    details.append(f"unexpected: {', '.join(sorted(unexpected))}")
                raise DataImportError(f"CSV header does not match the required schema ({'; '.join(details)})")
            for row in reader:
                line_number = reader.line_num
                if not row:
                    continue
                if len(row) != len(fieldnames):
                    yield line_number, RecordValidationError(
                        "record has a different number of fields than the header",
                        line_number=line_number,
                    )
                    continue
                try:
                    values = dict(zip(fieldnames, row, strict=True))
                    yield line_number, parse_vehicle(values, line_number, config)
                except RecordValidationError as error:
                    yield line_number, error
    except OSError as error:
        raise DataImportError(f"Cannot read input CSV: {path}") from error
    except UnicodeError as error:
        raise DataImportError("Input CSV is not valid UTF-8") from error
    except csv.Error as error:
        raise DataImportError("Malformed CSV input") from error
