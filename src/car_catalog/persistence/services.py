"""Transactional application services for persisted catalog operations."""

from collections.abc import Mapping

from sqlalchemy.orm import Session, sessionmaker

from car_catalog.persistence.models import ManufacturerRecord
from car_catalog.persistence.repositories import CarRepository


class CarCatalogService:
    """Coordinates catalog operations that span multiple repository writes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def update_prices_for_manufacturer(
        self,
        manufacturer_id: int,
        price_updates: Mapping[int, float],
    ) -> int:
        """Atomically update selected prices or roll every change back."""
        if manufacturer_id <= 0:
            raise ValueError("Manufacturer ID must be positive")
        with self._session_factory.begin() as session:
            manufacturer = session.get(ManufacturerRecord, manufacturer_id)
            if manufacturer is None:
                raise LookupError(f"Manufacturer {manufacturer_id} does not exist")
            repository = CarRepository(session)
            for car_id, price in price_updates.items():
                car = repository.get_by_id(car_id)
                if car is None:
                    raise LookupError(f"Car {car_id} does not exist")
                if car.manufacturer_id != manufacturer_id:
                    raise ValueError(f"Car {car_id} does not belong to manufacturer {manufacturer_id}")
                repository.update(car_id, price=price)
        return len(price_updates)
