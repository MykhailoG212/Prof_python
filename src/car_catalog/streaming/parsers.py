"""Потоковий розбір CSV-записів."""

import csv
from collections.abc import Iterable, Iterator

CsvRow = dict[str | None, object]


def parse_csv_rows(lines: Iterable[str]) -> Iterator[CsvRow]:
    """Перетворює CSV-рядки на словники за назвами колонок."""
    yield from csv.DictReader(lines, skipinitialspace=True)
