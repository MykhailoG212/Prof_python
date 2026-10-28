"""Порівняння eager та streaming обробки CSV для ЛР5."""

import csv
import hashlib
import json
import tempfile
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from car_catalog.reliable.exceptions import RecordValidationError
from car_catalog.reliable.importers import read_vehicles
from car_catalog.reliable.models import ProcessingConfig, Vehicle

_FIELDS = ("vehicle_id", "brand", "model", "year", "price", "mileage")
_DEFAULT_SIZE = 100_000
_CONFIG = ProcessingConfig(
    minimum_year=1886,
    maximum_year=2026,
    minimum_price=0,
    maximum_price=1_000_000,
    invalid_record_policy="tolerant",
)


@dataclass(frozen=True, slots=True)
class Summary:
    valid_count: int
    invalid_count: int
    sha256: str


@dataclass(frozen=True, slots=True)
class Measurement:
    mode: str
    elapsed_seconds: float
    peak_memory_bytes: int
    summary: Summary


def write_synthetic_dataset(path: Path, size: int, invalid_every: int = 10_000) -> None:
    """Створює відтворюваний набір CSV для вимірювання імпорту."""
    if size < 0:
        raise ValueError("size must not be negative")
    if invalid_every < 0:
        raise ValueError("invalid_every must not be negative")

    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(_FIELDS)
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
                writer.writerow((f"invalid-{index}", "Broken", "Record", 2020, "not-a-price", -1))


def _summary(records: Iterable[tuple[int, Vehicle | RecordValidationError]]) -> Summary:
    valid_count = 0
    invalid_count = 0
    digest = hashlib.sha256()
    for _, result in records:
        if isinstance(result, RecordValidationError):
            invalid_count += 1
            continue
        valid_count += 1
        serialized = json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest.update(serialized.encode("utf-8"))
        digest.update(b"\n")
    return Summary(valid_count, invalid_count, digest.hexdigest())


def _process_streaming(path: Path) -> Summary:
    return _summary(read_vehicles(path, _CONFIG))


def _process_eager(path: Path) -> Summary:
    records = list(read_vehicles(path, _CONFIG))
    return _summary(records)


def _measure(mode: str, process: Callable[[Path], Summary], path: Path) -> Measurement:
    tracemalloc.start()
    try:
        started = perf_counter()
        summary = process(path)
        elapsed = perf_counter() - started
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return Measurement(mode, elapsed, peak_memory, summary)


def compare_processing(path: Path) -> tuple[Measurement, Measurement]:
    """Вимірює обидва режими на одному файлі та звіряє точний JSON-відбиток."""
    eager = _measure("eager", _process_eager, path)
    streaming = _measure("streaming", _process_streaming, path)
    if eager.summary != streaming.summary:
        raise RuntimeError("Eager and streaming imports produced different results")
    return eager, streaming


def measure_benchmark(size: int = _DEFAULT_SIZE) -> tuple[Measurement, Measurement]:
    """Генерує тестовий CSV і повертає порівнювані вимірювання."""
    with tempfile.TemporaryDirectory(prefix="car-catalog-lab5-") as directory:
        path = Path(directory) / "vehicles.csv"
        write_synthetic_dataset(path, size)
        return compare_processing(path)


def run_benchmark() -> None:
    """Друкує відтворюване порівняння eager та streaming обробки."""
    eager, streaming = measure_benchmark(_DEFAULT_SIZE)
    print(f"Dataset: {_DEFAULT_SIZE:,} valid candidates plus malformed control rows")
    print(f"{'Mode':<10} | {'Time, s':>10} | {'Peak memory, MiB':>18} | {'Valid':>10} | {'Invalid':>10}")
    print("-" * 70)
    for result in (eager, streaming):
        peak_mib = result.peak_memory_bytes / (1024 * 1024)
        print(
            f"{result.mode:<10} | {result.elapsed_seconds:>10.4f} | {peak_mib:>18.3f} | "
            f"{result.summary.valid_count:>10,} | {result.summary.invalid_count:>10,}"
        )
    print(f"Results match (SHA-256): {eager.summary.sha256}")


if __name__ == "__main__":
    run_benchmark()
