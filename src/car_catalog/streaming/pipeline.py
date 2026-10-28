"""Побудова lazy pipeline для одного або кількох CSV-файлів."""

from collections.abc import Generator, Iterable, Iterator
from itertools import chain
from pathlib import Path

from car_catalog.streaming.filters import filter_cars
from car_catalog.streaming.models import CarRecord, ValidationStats
from car_catalog.streaming.parsers import parse_csv_rows
from car_catalog.streaming.readers import clean_lines, read_lines
from car_catalog.streaming.validation import validate_car_rows


def iter_car_records(
    paths: Iterable[Path],
    stats: ValidationStats | None = None,
) -> Generator[CarRecord, None, None]:
    """Потоково читає, очищує, розбирає та валідує CSV з одного чи кількох файлів."""
    rows = chain.from_iterable(parse_csv_rows(clean_lines(read_lines(path))) for path in paths)
    yield from validate_car_rows(rows, stats)


def build_pipeline(
    paths: Iterable[Path],
    brand: str | None = None,
    year: int | None = None,
    stats: ValidationStats | None = None,
) -> Iterator[CarRecord]:
    """Збирає lazy pipeline: source → parse → validate → filter."""
    return filter_cars(iter_car_records(paths, stats), brand=brand, year=year)
