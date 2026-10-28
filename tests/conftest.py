from collections.abc import Callable

import pytest

from car_catalog.models import Car
from car_catalog.reliable.models import ProcessingConfig


@pytest.fixture
def car_factory() -> Callable[..., Car]:
    def create_car(
        *,
        brand: str = "Toyota",
        model: str = "Camry",
        year: int = 2020,
        price: float = 25_000.0,
        mileage: int = 45_000,
    ) -> Car:
        return Car(brand, model, year, price, mileage)

    return create_car


@pytest.fixture(scope="session")
def processing_config() -> ProcessingConfig:
    return ProcessingConfig(
        minimum_year=1886,
        maximum_year=2026,
        minimum_price=0.0,
        maximum_price=1_000_000.0,
        invalid_record_policy="tolerant",
    )
