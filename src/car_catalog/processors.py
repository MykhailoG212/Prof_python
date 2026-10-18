"""Обробка колекцій даних про автомобілі."""

from collections import Counter, defaultdict

from car_catalog.models import Car


def get_unique_brands(cars: list[Car]) -> set[str]:
    """Повертає множину марок автомобілів за допомогою set comprehension."""
    return {car.brand for car in cars}


def build_cars_by_id_index(cars: list[Car]) -> dict[int, Car]:
    """Будує індекс автомобілів за 1-based порядковим ID у каталозі."""
    return {car_id: car for car_id, car in enumerate(cars, start=1)}


def count_cars_by_brand(cars: list[Car]) -> Counter[str]:
    """Підраховує кількість автомобілів кожної марки."""
    return Counter(car.brand for car in cars)


def group_cars_by_brand(cars: list[Car]) -> dict[str, list[Car]]:
    """Групує автомобілі за маркою, використовуючи defaultdict."""
    grouped: defaultdict[str, list[Car]] = defaultdict(list)
    for car in cars:
        grouped[car.brand].append(car)
    return dict(grouped)


def extract_cars_brief_tuples(cars: list[Car]) -> list[tuple[str, str, int]]:
    """Повертає короткі незмінні записи (марка, модель, рік)."""
    return [(car.brand, car.model, car.year) for car in cars]
