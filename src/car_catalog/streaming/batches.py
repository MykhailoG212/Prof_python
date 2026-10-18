"""Обробка потоків пакетами."""

from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def batched(items: Iterable[T], batch_size: int) -> Iterator[list[T]]:
    """Ділить довільний iterable на послідовні пакети заданого розміру."""
    if batch_size < 1:
        raise ValueError("Розмір пакета має бути не меншим за 1.")

    iterator = iter(items)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def flatten_batches(batches: Iterable[Iterable[T]]) -> Iterator[T]:
    """Об'єднує пакети через yield from без створення спільного списку."""
    for batch in batches:
        yield from batch
