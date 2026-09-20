from car_catalog.models import Car


def filter_by_make(cars: list[Car], make: str) -> list[Car]:
    """Повертає список авто відповідної марки (без урахування регістру)."""
    normalized_make = make.strip().casefold()
    return [car for car in cars if car.make.casefold() == normalized_make]


def filter_by_year(cars: list[Car], year: int) -> list[Car]:
    """Повертає список авто за вказаним роком випуску."""
    return [car for car in cars if car.year == year]


def find_most_expensive_car(cars: list[Car]) -> Car | None:
    """Знаходить автомобіль із найвищою ціною."""
    return max(cars, key=lambda car: car.price, default=None)


def find_lowest_mileage_car(cars: list[Car]) -> Car | None:
    """Знаходить автомобіль із найменшим пробігом."""
    return min(cars, key=lambda car: car.mileage, default=None)


def calculate_average_price(cars: list[Car]) -> float:
    """Обчислює середню ціну списку автомобілів."""
    if not cars:
        return 0.0
    return sum(car.price for car in cars) / len(cars)
