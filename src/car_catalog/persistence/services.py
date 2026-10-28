"""Transactional application services for persisted catalog operations."""

from collections.abc import Mapping
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from car_catalog.persistence.models import CarRecord, ManufacturerRecord
from car_catalog.persistence.repositories import CarRepository


class BrandStatistics(TypedDict):
    """Aggregated car inventory metrics for one manufacturer."""

    brand: str
    count: int
    avg_price: float
    max_price: float
    total_value: float


class CatalogStatistics(TypedDict):
    """Price and mileage highlights for the complete catalog."""

    average_price: float
    most_expensive_car: CarRecord | None
    lowest_mileage_car: CarRecord | None


class CarCatalogService:
    """Coordinates catalog operations that span multiple repository writes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_brand_statistics(self) -> list[BrandStatistics]:
        """Return per-manufacturer inventory counts and price aggregates."""
        car_count = func.count(CarRecord.id)
        statement = (
            select(
                ManufacturerRecord.name,
                car_count,
                func.avg(CarRecord.price),
                func.max(CarRecord.price),
                func.sum(CarRecord.price),
            )
            .join(CarRecord, CarRecord.manufacturer_id == ManufacturerRecord.id)
            .group_by(ManufacturerRecord.id, ManufacturerRecord.name)
            .order_by(car_count.desc(), ManufacturerRecord.name)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()
        return [
            {
                "brand": brand,
                "count": int(count),
                "avg_price": round(float(average_price), 2),
                "max_price": float(max_price),
                "total_value": float(total_value),
            }
            for brand, count, average_price, max_price, total_value in rows
        ]

    def get_catalog_statistics(self) -> CatalogStatistics:
        """Return aggregate price and car records using one database session."""
        with self._session_factory() as session:
            repository = CarRepository(session)
            return {
                "average_price": repository.average_price(),
                "most_expensive_car": repository.most_expensive(),
                "lowest_mileage_car": repository.lowest_mileage(),
            }

    def get_average_price(self) -> float:
        """Return the average price across the catalog."""
        with self._session_factory() as session:
            return CarRepository(session).average_price()

    def get_most_expensive_car(self) -> CarRecord | None:
        """Return the most expensive car, if the catalog is not empty."""
        with self._session_factory() as session:
            return CarRepository(session).most_expensive()

    def get_lowest_mileage_car(self) -> CarRecord | None:
        """Return the car with the lowest mileage, if the catalog is not empty."""
        with self._session_factory() as session:
            return CarRepository(session).lowest_mileage()

    def update_price(self, car_id: int, price: float) -> bool:
        """Update one car's price in its own transaction."""
        with self._session_factory.begin() as session:
            return CarRepository(session).update_price(car_id, price) is not None

    def update_mileage(self, car_id: int, mileage: int) -> bool:
        """Update one car's mileage in its own transaction."""
        with self._session_factory.begin() as session:
            return CarRepository(session).update_mileage(car_id, mileage) is not None

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

    def bulk_update_manufacturer_prices(
        self,
        manufacturer_id: int,
        price_updates: Mapping[int, float],
    ) -> int:
        """Update selected manufacturer prices atomically."""
        return self.update_prices_for_manufacturer(manufacturer_id, price_updates)


CarCatalogDbService = CarCatalogService
