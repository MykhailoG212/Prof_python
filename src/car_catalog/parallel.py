"""Потокова/процесна аналітика, паралельне читання та синхронізація."""

import csv
import json
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Barrier, Lock, Thread
from typing import Any

from car_catalog.analytics import (
    AnalyticsResult,
    BenchmarkCar,
    CarData,
    analyze_cars,
    merge_analytics_results,
)


def _validate_workers(workers: int) -> None:
    if workers < 1:
        raise ValueError("Кількість workers має бути не меншою за 1.")


def _chunks(cars: Sequence[CarData], workers: int) -> list[tuple[CarData, ...]]:
    chunk_count = min(workers, len(cars))
    if chunk_count == 0:
        return []
    chunk_size = (len(cars) + chunk_count - 1) // chunk_count
    return [tuple(cars[start : start + chunk_size]) for start in range(0, len(cars), chunk_size)]


def _analyze_chunk(cars: tuple[CarData, ...]) -> AnalyticsResult:
    """Top-level callable, який pickle-иться для Windows spawn."""
    return analyze_cars(cars)


def analyze_cars_with_threads(cars: Sequence[CarData], workers: int = 4) -> AnalyticsResult:
    """Розподіляє CPU-bound обчислення між потоками (для порівняння з GIL)."""
    _validate_workers(workers)
    chunks = _chunks(cars, workers)
    if not chunks:
        return analyze_cars(())
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_analyze_chunk, chunks))
    return merge_analytics_results(results)


def analyze_cars_with_processes(cars: Sequence[CarData], workers: int = 4) -> AnalyticsResult:
    """Розподіляє CPU-bound обчислення між процесами, включно з Windows spawn."""
    _validate_workers(workers)
    chunks = _chunks(cars, workers)
    if not chunks:
        return analyze_cars(())
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_analyze_chunk, chunks))
    return merge_analytics_results(results)


def _parse_car_record(record: dict[str, Any], index: int) -> BenchmarkCar:
    brand = record.get("brand", record.get("manufacturer", record.get("make")))
    required = ("model", "year", "price", "mileage")
    if not isinstance(brand, str) or not brand.strip():
        raise ValueError(f"Запис {index}: відсутня коректна марка автомобіля.")
    if any(field not in record for field in required):
        raise ValueError(f"Запис {index}: обов'язкові поля: {', '.join(required)}.")
    model = record["model"]
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"Запис {index}: відсутня коректна модель автомобіля.")
    try:
        year = int(record["year"])
        price = float(record["price"])
        mileage = int(record["mileage"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"Запис {index}: рік, ціна або пробіг мають некоректний формат.") from error
    vin = record.get("vin", f"FILE{index:013d}")
    if not isinstance(vin, str):
        raise ValueError(f"Запис {index}: VIN має бути текстовим значенням.")
    if year < 1886 or price < 0 or mileage < 0:
        raise ValueError(f"Запис {index}: рік, ціна чи пробіг поза допустимими межами.")
    return BenchmarkCar(brand.strip(), model.strip(), year, price, mileage, vin)


def _load_catalog_file(file_path: Path) -> list[BenchmarkCar]:
    suffix = file_path.suffix.casefold()
    if suffix == ".json":
        with file_path.open("r", encoding="utf-8") as file:
            payload: Any = json.load(file)
        if isinstance(payload, dict):
            payload = payload.get("cars")
        if not isinstance(payload, list):
            raise ValueError(f"{file_path}: JSON має містити масив записів або об'єкт із ключем 'cars'.")
        records = payload
    elif suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as file:
            records = list(csv.DictReader(file))
    else:
        raise ValueError(f"Непідтримуваний формат файлу: {file_path.suffix}")

    cars: list[BenchmarkCar] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"{file_path}: запис {index} має бути JSON-об'єктом.")
        cars.append(_parse_car_record(record, index))
    return cars


def load_catalog_files(paths: Sequence[str | Path], workers: int = 4) -> list[BenchmarkCar]:
    """Паралельно читає JSON/CSV-файли, зберігаючи порядок вхідних файлів."""
    _validate_workers(workers)
    file_paths = [Path(path) for path in paths]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        batches = list(executor.map(_load_catalog_file, file_paths))
    return [car for batch in batches for car in batch]


@dataclass(frozen=True, slots=True)
class RaceConditionResult:
    """Результати контрольованого конкурентного оновлення лічильника."""

    expected: int
    unsynchronized: int
    synchronized: int


def demonstrate_race_condition(iterations: int = 500, workers: int = 8) -> RaceConditionResult:
    """Порівнює незахищений лічильник із варіантом, синхронізованим Lock."""
    if iterations < 1:
        raise ValueError("Кількість ітерацій має бути не меншою за 1.")
    _validate_workers(workers)

    unsynchronized_counter = [0]
    start_barrier = Barrier(workers)

    def unsafe_increment() -> None:
        start_barrier.wait()
        for _ in range(iterations):
            current = unsynchronized_counter[0]
            time.sleep(0)
            unsynchronized_counter[0] = current + 1

    unsafe_threads = [Thread(target=unsafe_increment) for _ in range(workers)]
    for thread in unsafe_threads:
        thread.start()
    for thread in unsafe_threads:
        thread.join()

    synchronized_counter = [0]
    lock = Lock()

    def safe_increment() -> None:
        for _ in range(iterations):
            with lock:
                synchronized_counter[0] += 1

    safe_threads = [Thread(target=safe_increment) for _ in range(workers)]
    for thread in safe_threads:
        thread.start()
    for thread in safe_threads:
        thread.join()

    expected = iterations * workers
    return RaceConditionResult(expected, unsynchronized_counter[0], synchronized_counter[0])
