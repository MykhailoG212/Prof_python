"""Коротка демонстрація потокового каталогу на вбудованому CSV-прикладі."""

from itertools import islice
from pathlib import Path

from car_catalog.streaming.analytics import calculate_statistics, group_cars_by_brand
from car_catalog.streaming.batches import batched
from car_catalog.streaming.models import ValidationStats
from car_catalog.streaming.pipeline import build_pipeline
from car_catalog.streaming.transformations import summarize_cars


def sample_data_path() -> Path:
    """Повертає шлях до навчального CSV у корені проєкту."""
    return Path(__file__).resolve().parents[3] / "data" / "cars.csv"


def run_demo() -> None:
    """Показує агрегацію, фільтрацію, трансформацію та batching."""
    path = sample_data_path()
    validation = ValidationStats()
    statistics = calculate_statistics(build_pipeline([path], stats=validation))
    print(
        f"Оброблено {statistics.count} автомобілів; "
        f"відхилено рядків: {validation.invalid_count}"
    )
    print(f"Середня ціна: ${statistics.average_price:,.2f}")
    if statistics.most_expensive is not None:
        print(f"Найдорожчий: {statistics.most_expensive.full_name}")
    if statistics.lowest_mileage is not None:
        print(f"Найменший пробіг: {statistics.lowest_mileage.full_name}")

    recent = build_pipeline([path], brand="Toyota", year=2020)
    print("Перші збіги:", list(islice(summarize_cars(recent), 3)))

    records = build_pipeline([path])
    print("Перший пакет:", next(batched(records, 3), []))
    groups = group_cars_by_brand(build_pipeline([path]))
    print("Групи марок:", [(brand, len(cars)) for brand, cars in groups])


if __name__ == "__main__":
    run_demo()
