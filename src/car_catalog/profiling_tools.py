"""Інструменти cProfile та tracemalloc для вимірювання ЛР9."""

import cProfile
import pstats
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO
from typing import TypeVar, cast

from car_catalog.analytics import analyze_cars, generate_dataset

R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class ProfileEntry:
    """Один рядок звіту профілювання функції."""

    function: str
    calls: int
    self_seconds: float
    cumulative_seconds: float


@dataclass(frozen=True, slots=True)
class ProfileReport:
    """Структуровані метрики та форматований звіт cProfile."""

    entries: tuple[ProfileEntry, ...]
    formatted_output: str


@dataclass(frozen=True, slots=True)
class MemoryMeasurement:
    """Поточний і піковий обсяг Python-алокацій у байтах."""

    current_bytes: int
    peak_bytes: int


def profile_function(
    function: Callable[..., R],
    *args: object,
    top_n: int = 20,
    sort_by: str = "cumulative",
    **kwargs: object,
) -> tuple[R, ProfileReport]:
    """Профілює виклик і повертає результат, ncalls/tottime/cumtime та cProfile."""
    if top_n < 1:
        raise ValueError("top_n має бути не меншим за 1.")
    if sort_by not in {"calls", "cumulative", "tottime", "time"}:
        raise ValueError("sort_by має бути calls, cumulative, tottime або time.")

    profiler = cProfile.Profile()
    result = profiler.runcall(function, *args, **kwargs)
    output = StringIO()
    stats = pstats.Stats(profiler, stream=output).strip_dirs().sort_stats(sort_by)
    stats.print_stats(top_n)

    entries: list[ProfileEntry] = []
    sort_index = {"calls": 1, "cumulative": 3, "tottime": 2, "time": 2}[sort_by]
    raw_stats = cast(
        dict[tuple[str, int, str], tuple[int, int, float, float, object]],
        getattr(stats, "stats"),
    )
    ordered_stats = sorted(
        raw_stats.items(),
            key=lambda item: (
                float(item[1][1])
                if sort_index == 1
                else item[1][3]
                if sort_index == 3
                else item[1][2]
            ),
            reverse=True,
        )[:top_n]
    for (filename, line_number, function_name), data in ordered_stats:
        _, total_calls, self_seconds, cumulative_seconds, _ = data
        entries.append(
            ProfileEntry(
                function=f"{filename}:{line_number}({function_name})",
                calls=total_calls,
                self_seconds=self_seconds,
                cumulative_seconds=cumulative_seconds,
            )
        )
    return result, ProfileReport(tuple(entries), output.getvalue())


def measure_memory(
    function: Callable[..., R],
    *args: object,
    **kwargs: object,
) -> tuple[R, MemoryMeasurement]:
    """Вимірює поточну й пікову Python-алокацію під час одного виклику."""
    if tracemalloc.is_tracing():
        raise RuntimeError("tracemalloc уже активний; зупиніть попередній вимір.")
    tracemalloc.start()
    try:
        result = function(*args, **kwargs)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, MemoryMeasurement(current_bytes, peak_bytes)


def _demo() -> None:
    cars = generate_dataset(10_000)
    result, report = profile_function(analyze_cars, cars, top_n=12)
    _, memory = measure_memory(analyze_cars, cars)
    print(f"Записів проаналізовано: {result.count}")
    print(f"Поточна пам'ять: {memory.current_bytes:,} байт")
    print(f"Пікова пам'ять: {memory.peak_bytes:,} байт")
    print(report.formatted_output)


if __name__ == "__main__":
    _demo()
