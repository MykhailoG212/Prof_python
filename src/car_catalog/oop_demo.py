"""Демонстрація об'єктної моделі ЛР4 для варіанта 5."""

from car_catalog.application import VehicleCatalogService
from car_catalog.models import Car, ElectricCar, Vehicle, VehicleSpecification
from car_catalog.repositories import InMemoryRepository


def run_demo() -> None:
    repository: InMemoryRepository[Vehicle] = InMemoryRepository()
    service = VehicleCatalogService(repository)
    service.add(Car("Toyota", "Camry", 2020, 25_000.0, 45_000))
    service.add(Car("BMW", "M3", 2022, 72_000.0, 18_000))
    service.add(
        ElectricCar(
            "Tesla", "Model 3", 2023, 41_000.0, 12_000,
            VehicleSpecification("Електро", "Автоматична", "Седан"), 513,
        )
    )

    print("\n--- ООП-модель каталогу (ЛР4, варіант 5) ---")
    print("Пошук Toyota:", [str(car) for car in service.search_by_brand_or_model(brand="Toyota")])
    print("Авто 2023 року:", [str(car) for car in service.filter_by_year(2023)])
    print("Найдорожче авто:", service.most_expensive())
    print(f"Середня ціна: ${service.average_price():,.2f}")
    print("Мінімальний пробіг:", service.lowest_mileage())


if __name__ == "__main__":
    run_demo()

