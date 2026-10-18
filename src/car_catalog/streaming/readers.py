"""Потокове читання вхідних файлів."""

from collections.abc import Iterable, Iterator
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Читає файл построково та закриває його після вичерпання генератора."""
    with path.open("r", encoding="utf-8", newline="") as source:
        yield from source


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Обрізає пробіли й пропускає порожні рядки, не матеріалізуючи потік."""
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            yield cleaned
