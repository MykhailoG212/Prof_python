"""Повторюваний benchmark аналітики каталогу (запускайте як окремий скрипт)."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import time
import tracemalloc
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from car_catalog.analytics import (
    AnalyticsResult,
    CachedCarAnalytics,
    analyze_cars,
    analyze_cars_numpy,
    generate_dataset,
    merge_analytics_results,
)
from car_catalog.parallel import analyze_cars_with_processes, analyze_cars_with_threads

DEFAULT_SIZES = (10_000, 100_000, 200_000)
DEFAULT_WORKERS = (1, 2, 4, 8)


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    dataset: int
    method: str
    workers: int
    mean_time: float
    peak_memory: int
    speedup: float


def _cached_analysis(cache: CachedCarAnalytics, brands: tuple[str, ...]) -> AnalyticsResult:
    parts: list[AnalyticsResult] = []
    for brand in brands:
        stats = cache.statistics_for_brand(brand)
        parts.append(
            AnalyticsResult(
                count=stats.count,
                average_price=stats.average_price,
                minimum_mileage=stats.minimum_mileage,
                maximum_mileage=stats.maximum_mileage,
                price_variance=stats.price_variance,
                price_standard_deviation=stats.price_standard_deviation,
                average_score=stats.average_score,
                brand_counts={brand: stats.count} if stats.count else {},
            )
        )
    return merge_analytics_results(parts)


def _results_match(expected: AnalyticsResult, actual: AnalyticsResult) -> bool:
    numeric_fields = (
        "average_price",
        "price_variance",
        "price_standard_deviation",
        "average_score",
    )
    return (
        expected.count == actual.count
        and expected.minimum_mileage == actual.minimum_mileage
        and expected.maximum_mileage == actual.maximum_mileage
        and expected.brand_counts == actual.brand_counts
        and all(
            math.isclose(
                getattr(expected, field),
                getattr(actual, field),
                rel_tol=1e-10,
                abs_tol=1e-8,
            )
            for field in numeric_fields
        )
    )


def _measure_peak_memory(operation: Callable[[], AnalyticsResult]) -> int:
    if tracemalloc.is_tracing():
        raise RuntimeError("tracemalloc уже активний.")
    tracemalloc.start()
    try:
        operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak


def _time_operation(
    operation: Callable[[], AnalyticsResult],
    expected: AnalyticsResult,
    repeats: int,
) -> tuple[float, int]:
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        actual = operation()
        samples.append(time.perf_counter() - started)
        if not _results_match(expected, actual):
            raise AssertionError("Оптимізований варіант повернув відмінні результати аналітики.")
    peak = _measure_peak_memory(operation)
    return statistics.fmean(samples), peak


def run_benchmarks(
    sizes: Sequence[int] = DEFAULT_SIZES,
    workers: Sequence[int] = DEFAULT_WORKERS,
    repeats: int = 5,
) -> list[BenchmarkRow]:
    """Запускає baseline, threading, multiprocessing, NumPy та прогрітий cache."""
    if repeats < 1:
        raise ValueError("Кількість повторів має бути не меншою за 1.")
    if not sizes or any(size < 1 for size in sizes):
        raise ValueError("Потрібно вказати принаймні один додатний розмір датасету.")
    if not workers or any(worker < 1 for worker in workers):
        raise ValueError("Кількість workers має бути додатною.")

    rows: list[BenchmarkRow] = []
    for size in sizes:
        cars = generate_dataset(size)
        baseline = analyze_cars(cars)

        def baseline_operation() -> AnalyticsResult:
            return analyze_cars(cars)

        baseline_time, baseline_peak = _time_operation(baseline_operation, baseline, repeats)
        rows.append(BenchmarkRow(size, "Baseline", 1, baseline_time, baseline_peak, 1.0))

        operations: list[tuple[str, int, Callable[[], AnalyticsResult]]] = []
        for worker_count in workers:
            def thread_operation(current_workers: int = worker_count) -> AnalyticsResult:
                return analyze_cars_with_threads(cars, current_workers)

            def process_operation(current_workers: int = worker_count) -> AnalyticsResult:
                return analyze_cars_with_processes(cars, current_workers)

            operations.append(
                (
                    "ThreadPool",
                    worker_count,
                    thread_operation,
                )
            )
            operations.append(
                (
                    "ProcessPool",
                    worker_count,
                    process_operation,
                )
            )
        operations.append(("NumPy", 1, lambda: analyze_cars_numpy(cars)))

        cache = CachedCarAnalytics(cars)
        brands = tuple(sorted(baseline.brand_counts))

        def cached_operation() -> AnalyticsResult:
            return _cached_analysis(cache, brands)

        cached_operation()
        operations.append(("Caching (warm)", 1, cached_operation))

        for method, worker_count, operation in operations:
            mean_time, peak_memory = _time_operation(operation, baseline, repeats)
            speedup = baseline_time / mean_time if mean_time else math.inf
            rows.append(BenchmarkRow(size, method, worker_count, mean_time, peak_memory, speedup))
    return rows


def render_table(rows: Sequence[BenchmarkRow]) -> str:
    """Форматує вимірювання у Markdown-таблицю."""
    headers = ("Dataset", "Method", "Workers", "Mean Time (s)", "Peak Memory (MiB)", "Speedup")
    rendered = ["| " + " | ".join(headers) + " |", "|---:|---|---:|---:|---:|---:|"]
    for row in rows:
        rendered.append(
            f"| {row.dataset:,} | {row.method} | {row.workers} | "
            f"{row.mean_time:.6f} | {row.peak_memory / (1024 * 1024):.2f} | {row.speedup:.2f}x |"
        )
    return "\n".join(rendered)


def _write_csv(path: Path, rows: Sequence[BenchmarkRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("dataset", "method", "workers", "mean_time_seconds", "peak_memory_bytes", "speedup"))
        for row in rows:
            writer.writerow(
                (row.dataset, row.method, row.workers, f"{row.mean_time:.9f}", row.peak_memory, f"{row.speedup:.6f}")
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--workers", type=int, nargs="+", default=list(DEFAULT_WORKERS))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--csv", type=Path, help="Додатково зберегти результати у CSV.")
    args = parser.parse_args()

    results = run_benchmarks(args.sizes, args.workers, args.repeats)
    print(render_table(results))
    print("\nSpeedup: Sp = T1 / Tp; baseline для кожного розміру має Sp = 1.00.")
    print("Peak Memory — Python allocations процесу-ініціатора; пам'ять дочірніх процесів не включена.")
    print("Час вимірюється без tracemalloc; пам'ять вимірюється окремим повторним запуском.")
    if args.csv:
        _write_csv(args.csv, results)
        print(f"\nCSV збережено: {args.csv}")


if __name__ == "__main__":
    main()
