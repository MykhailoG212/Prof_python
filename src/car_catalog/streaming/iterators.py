"""Приклади власного iterator та контрольованого нескінченного generator."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import count, islice


class CarIdIterator(Iterator[int]):
    """Власний одноразовий iterator послідовних додатних ID автомобілів."""

    def __init__(self, start: int = 1, stop: int | None = None) -> None:
        if start < 1:
            raise ValueError("Початковий ID має бути додатним.")
        if stop is not None and stop < start:
            raise ValueError("Кінцевий ID не може бути меншим за початковий.")
        self._current = start
        self._stop = stop

    def __iter__(self) -> CarIdIterator:
        return self

    def __next__(self) -> int:
        if self._stop is not None and self._current >= self._stop:
            raise StopIteration
        current = self._current
        self._current += 1
        return current


def infinite_car_ids(start: int = 1) -> Iterator[int]:
    """Генерує нескінченний потік ID; споживач має обмежити його islice."""
    if start < 1:
        raise ValueError("Початковий ID має бути додатним.")
    yield from count(start)


def first_car_ids(limit: int, start: int = 1) -> Iterator[int]:
    """Безпечно бере скінченний префікс нескінченного потоку."""
    if limit < 0:
        raise ValueError("Ліміт має бути невід'ємним.")
    return islice(infinite_car_ids(start), limit)


def flatten_nested(values: object) -> Iterator[object]:
    """Рекурсивно розгортає вкладені списки й кортежі через yield from."""
    if isinstance(values, (list, tuple)):
        for value in values:
            yield from flatten_nested(value)
    else:
        yield values
