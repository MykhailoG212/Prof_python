from dataclasses import FrozenInstanceError

import pytest

from car_catalog.application import VehicleCatalogService
from car_catalog.criteria import BrandModelCriteria, YearCriteria
from car_catalog.dto import VehicleData
from car_catalog.models import Car, ElectricCar, Vehicle, VehicleSpecification
from car_catalog.protocols import SearchCriteria
from car_catalog.repositories import InMemoryRepository, VehicleCatalog


def electric_car() -> ElectricCar:
    return ElectricCar(
        "Tesla",
        "Model 3",
        2023,
        41_000.0,
        12_000,
        VehicleSpecification("Електро", "Автоматична", "Седан"),
        513,
    )


def test_vehicle_hierarchy_and_frozen_specification() -> None:
    car = Car("Toyota", "Camry", 2020, 25_000.0, 45_000)
    electric = electric_car()

    assert isinstance(car, Vehicle)
    assert isinstance(electric, Car)
    assert car.full_name == "Toyota Camry"
    assert str(car) == "Toyota Camry (2020) — $25,000.00"
    with pytest.raises(FrozenInstanceError):
        electric.specification.fuel_type = "Бензин"  # type: ignore[misc]


def test_vehicle_and_specification_validation() -> None:
    with pytest.raises(ValueError, match="не можуть бути порожніми"):
        VehicleSpecification("", "Автоматична", "Седан")
    with pytest.raises(ValueError, match="1800"):
        Car("Toyota", "Oldtimer", 1800, 1_000.0, 0)
    with pytest.raises(ValueError, match="скінченною"):
        Car("Toyota", "Camry", 2020, float("inf"), 0)


def test_electric_car_requires_valid_range_and_electric_specification() -> None:
    with pytest.raises(ValueError, match="додатним"):
        ElectricCar(
            "Tesla", "Model 3", 2023, 41_000.0, 12_000,
            VehicleSpecification("Електро", "Автоматична", "Седан"), 0,
        )
    with pytest.raises(ValueError, match="тип пального"):
        ElectricCar("Tesla", "Model 3", 2023, 41_000.0, 12_000, range_km=513)


def test_generic_repository_validates_ids_and_returns_entries() -> None:
    repository: InMemoryRepository[Car] = InMemoryRepository()
    car = Car("Toyota", "Camry", 2020, 25_000.0, 45_000)

    with pytest.raises(ValueError, match="додатним"):
        repository.add(0, car)
    repository.add(1, car)
    assert repository.get(1) == car
    assert repository.get(2) is None
    assert list(repository.all()) == [car]


def test_vehicle_catalog_collection_dunder_methods() -> None:
    catalog = VehicleCatalog()
    first = Car("Toyota", "Camry", 2020, 25_000.0, 45_000)
    second = electric_car()
    first_id = catalog.add(first)
    second_id = catalog.add(second)

    assert (first_id, second_id) == (1, 2)
    assert len(catalog) == 2
    assert list(catalog) == [first, second]
    assert 1 in catalog
    assert 3 not in catalog
    assert catalog[2] == second
    with pytest.raises(KeyError):
        _ = catalog[3]


def test_criteria_are_structurally_compatible_and_match_case_insensitively() -> None:
    vehicle = electric_car()
    criteria: SearchCriteria[Vehicle] = BrandModelCriteria("tesla", "MODEL 3")

    assert isinstance(criteria, SearchCriteria)
    assert criteria.matches(vehicle)
    assert not BrandModelCriteria("Tesla", "Roadster").matches(vehicle)
    assert YearCriteria(2023).matches(vehicle)
    assert not YearCriteria(2022).matches(vehicle)


def test_application_service_adds_searches_and_calculates_statistics() -> None:
    repository: InMemoryRepository[Vehicle] = InMemoryRepository()
    service = VehicleCatalogService(repository)
    cars: list[Vehicle] = [
        Car("Toyota", "Camry", 2020, 25_000.0, 45_000),
        Car("BMW", "M3", 2022, 72_000.0, 18_000),
        electric_car(),
    ]

    assert [service.add(car) for car in cars] == [1, 2, 3]
    assert service.search_by_brand_or_model(brand="TOYOTA") == [cars[0]]
    assert service.search_by_brand_or_model(model="Model 3") == [cars[2]]
    assert service.filter_by_year(2023) == [cars[2]]
    assert service.most_expensive() == cars[1]
    assert service.average_price() == pytest.approx(46_000.0)
    assert service.lowest_mileage() == cars[2]


def test_application_service_handles_empty_repository_and_typed_dto() -> None:
    repository: InMemoryRepository[Vehicle] = InMemoryRepository()
    service = VehicleCatalogService(repository)

    assert service.most_expensive() is None
    assert service.lowest_mileage() is None
    assert service.average_price() == 0.0

    car = electric_car()
    data: VehicleData = service.to_data(7, car)
    assert data == {
        "id": 7,
        "brand": "Tesla",
        "model": "Model 3",
        "year": 2023,
        "price": 41_000.0,
        "mileage": 12_000,
        "kind": "electric",
    }
