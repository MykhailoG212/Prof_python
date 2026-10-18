"""Декоратори для вимірювання часу та повторного виконання функцій."""

from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    """Вимірює та друкує тривалість виконання функції."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start_time = perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = perf_counter() - start_time
            print(f"[BENCHMARK] {func.__name__} виконано за {elapsed:.8f} с")

    return cast(Callable[P, R], wrapper)


def repeat(count: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Параметризований декоратор, що виконує функцію задану кількість разів."""
    if count < 1:
        raise ValueError("Кількість повторень має бути не меншою за 1.")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            for _ in range(count - 1):
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator
