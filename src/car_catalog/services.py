from car_catalog.models import Car


def find_by_brand(cars: list[Car], brand: str) -> list[Car]:
    """Повертає список авто відповідної марки (без урахування регістру)."""
    normalized_brand = brand.strip().casefold()
    return [car for car in cars if car.brand.casefold() == normalized_brand]


def filter_by_year(cars: list[Car], year: int) -> list[Car]:
    """Повертає список авто за вказаним роком випуску."""
    return [car for car in cars if car.year == year]


def find_most_expensive(cars: list[Car]) -> Car | None:
    """Знаходить автомобіль із найвищою ціною."""
    return max(cars, key=lambda car: car.price, default=None)


def find_lowest_mileage(cars: list[Car]) -> Car | None:
    """Знаходить автомобіль із найменшим пробігом."""
    return min(cars, key=lambda car: car.mileage, default=None)


def calculate_average_price(cars: list[Car]) -> float:
    """Обчислює середню ціну списку автомобілів."""
    if not cars:
        return 0.0
    return sum(car.price for car in cars) / len(cars)
