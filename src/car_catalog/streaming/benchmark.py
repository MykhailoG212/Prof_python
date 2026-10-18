"""Вимірювання часу й peak memory для eager та lazy CSV-процесингу."""

import csv
import tempfile
import tracemalloc
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from time import perf_counter
from typing import Callable

from car_catalog.streaming.analytics import calculate_statistics
from car_catalog.streaming.models import CarStatistics, ValidationStats
from car_catalog.streaming.parsers import parse_csv_rows
from car_catalog.streaming.pipeline import iter_car_records
from car_catalog.streaming.validation import validate_car_rows

CSV_HEADER = ("id", "brand", "model", "year", "price", "mileage")


@dataclass(frozen=True, slots=True)
class ProcessingMeasurement:
    """Результати одного запуску обробки набору даних."""

    mode: str
    elapsed_seconds: float
    peak_memory_bytes: int
    time_to_first_record_seconds: float
    statistics: CarStatistics
    validation: ValidationStats


def write_synthetic_dataset(path: Path, size: int, invalid_every: int = 0) -> None:
    """Створює відтворюваний CSV заданого розміру для локальних експериментів."""
    if size < 0:
        raise ValueError("Розмір набору не може бути від'ємним.")
    if invalid_every < 0:
        raise ValueError("Інтервал некоректних рядків не може бути від'ємним.")

    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(CSV_HEADER)
        for index in range(1, size + 1):
            writer.writerow(
                (
                    index,
                    f"Brand_{index % 50:02d}",
                    f"Model_{index}",
                    2000 + index % 25,
                    f"{10_000 + index % 90_000:.2f}",
                    index * 7 % 250_000,
                )
            )
            if invalid_every and index % invalid_every == 0:
                writer.writerow((f"invalid-{index}", "Broken", "Record", 2020, "NaN", -1))


def _measure(
    mode: str,
    process: Callable[[Path], tuple[CarStatistics, ValidationStats]],
    first_record: Callable[[Path], None],
    path: Path,
) -> ProcessingMeasurement:
    start = perf_counter()
    first_record(path)
    time_to_first = perf_counter() - start

    tracemalloc.start()
    try:
        start = perf_counter()
        statistics, validation = process(path)
        elapsed = perf_counter() - start
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return ProcessingMeasurement(
        mode=mode,
        elapsed_seconds=elapsed,
        peak_memory_bytes=peak_memory,
        time_to_first_record_seconds=time_to_first,
        statistics=statistics,
        validation=validation,
    )


def _process_eager(path: Path) -> tuple[CarStatistics, ValidationStats]:
    contents = path.read_text(encoding="utf-8")
    rows = parse_csv_rows(StringIO(contents))
    validation = ValidationStats()
    cars = list(validate_car_rows(rows, validation))
    return calculate_statistics(cars), validation


def _process_lazy(path: Path) -> tuple[CarStatistics, ValidationStats]:
    validation = ValidationStats()
    statistics = calculate_statistics(iter_car_records([path], validation))
    return statistics, validation


def _eager_time_to_first(path: Path) -> None:
    contents = path.read_text(encoding="utf-8")
    rows = parse_csv_rows(StringIO(contents))
    next(validate_car_rows(rows))


def _lazy_time_to_first(path: Path) -> None:
    records = iter_car_records([path])
    try:
        next(records)
    finally:
        records.close()


def compare_processing(path: Path) -> tuple[ProcessingMeasurement, ProcessingMeasurement]:
    """Порівнює обидва режими на тому самому файлі та звіряє результати."""
    eager = _measure("eager", _process_eager, _eager_time_to_first, path)
    lazy = _measure("lazy", _process_lazy, _lazy_time_to_first, path)
    if eager.statistics != lazy.statistics:
        raise RuntimeError("Eager і lazy обробка дали різні агрегати.")
    if eager.validation.valid_count != lazy.validation.valid_count:
        raise RuntimeError("Eager і lazy обробка виявили різну кількість валідних записів.")
    if eager.validation.invalid_count != lazy.validation.invalid_count:
        raise RuntimeError("Eager і lazy обробка виявили різну кількість помилок.")
    return eager, lazy


def run_benchmark(size: int = 100_000) -> None:
    """Генерує CSV і друкує порівняння часу, пам'яті та часу першого результату."""
    with tempfile.TemporaryDirectory(prefix="car-catalog-lab3-") as temp_dir:
        path = Path(temp_dir) / "cars.csv"
        write_synthetic_dataset(path, size, invalid_every=10_000)
        eager, lazy = compare_processing(path)

    print(f"Набір: {size:,} валідних авто плюс некоректні тестові рядки")
    print(
        f"{'Режим':<8} | {'Час, с':>12} | {'Peak memory, MiB':>18} | "
        f"{'До 1-го запису, с':>19} | {'Валідні':>10} | {'Некоректні':>11}"
    )
    print("-" * 94)
    for result in (eager, lazy):
        peak_mib = result.peak_memory_bytes / (1024 * 1024)
        print(
            f"{result.mode:<8} | {result.elapsed_seconds:>12.4f} | {peak_mib:>18.3f} | "
            f"{result.time_to_first_record_seconds:>19.6f} | "
            f"{result.validation.valid_count:>10,} | {result.validation.invalid_count:>11,}"
        )

    print(
        "\nВисновок: lazy pipeline не зберігає весь CSV та підтримує раннє "
        "завершення; eager обробка може бути простішою й швидшою на малих даних."
    )


if __name__ == "__main__":
    run_benchmark()
