"""Repository Pattern implementations for catalog persistence."""

import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from car_catalog.persistence.models import CarRecord, ManufacturerRecord


class ManufacturerRepository:
    """CRUD operations for manufacturers using a caller-managed session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, name: str, country: str = "Unknown") -> ManufacturerRecord:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Manufacturer name cannot be empty")
        normalized_country = country.strip()
        if not normalized_country:
            raise ValueError("Manufacturer country cannot be empty")
        manufacturer = ManufacturerRecord(
            name=normalized_name,
            country=normalized_country,
        )
        self._session.add(manufacturer)
        self._session.flush()
        return manufacturer

    def get_by_id(self, manufacturer_id: int) -> ManufacturerRecord | None:
        return self._session.get(ManufacturerRecord, manufacturer_id)

    def get_by_name(self, name: str) -> ManufacturerRecord | None:
        statement = select(ManufacturerRecord).where(
            func.lower(ManufacturerRecord.name) == name.strip().casefold()
        )
        return self._session.scalar(statement)

    def list_all(self) -> list[ManufacturerRecord]:
        statement = select(ManufacturerRecord).order_by(ManufacturerRecord.id)
        return list(self._session.scalars(statement))

    def update(self, manufacturer_id: int, name: str) -> ManufacturerRecord | None:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Manufacturer name cannot be empty")
        manufacturer = self.get_by_id(manufacturer_id)
        if manufacturer is None:
            return None
        manufacturer.name = normalized_name
        self._session.flush()
        return manufacturer

    def delete(self, manufacturer_id: int) -> bool:
        manufacturer = self.get_by_id(manufacturer_id)
        if manufacturer is None:
            return False
        self._session.delete(manufacturer)
        self._session.flush()
        return True


class CarRepository:
    """CRUD, filtering and aggregation for persisted cars."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        manufacturer_id: int,
        model: str,
        year: int,
        price: float,
        mileage: int,
        vin: str | None,
    ) -> CarRecord:
        self._validate_car_data(model, year, price, mileage, vin)
        if self._session.get(ManufacturerRecord, manufacturer_id) is None:
            raise LookupError(f"Manufacturer {manufacturer_id} does not exist")
        car = CarRecord(
            manufacturer_id=manufacturer_id,
            model=model.strip(),
            year=year,
            price=price,
            mileage=mileage,
            vin=vin.strip() if vin is not None else None,
        )
        self._session.add(car)
        self._session.flush()
        return car

    def get_by_id(self, car_id: int) -> CarRecord | None:
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .where(CarRecord.id == car_id)
        )
        return self._session.scalar(statement)

    def get_by_vin(self, vin: str) -> CarRecord | None:
        statement = select(CarRecord).where(CarRecord.vin == vin.strip())
        return self._session.scalar(statement)

    def list_all(self) -> list[CarRecord]:
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .order_by(CarRecord.id)
        )
        return list(self._session.scalars(statement).unique())

    def find_by_manufacturer(self, manufacturer_name: str) -> list[CarRecord]:
        statement = (
            select(CarRecord)
            .join(CarRecord.manufacturer)
            .options(joinedload(CarRecord.manufacturer))
            .where(func.lower(ManufacturerRecord.name) == manufacturer_name.strip().casefold())
            .order_by(CarRecord.id)
        )
        return list(self._session.scalars(statement).unique())

    def filter_by_year(self, year: int) -> list[CarRecord]:
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .where(CarRecord.year == year)
            .order_by(CarRecord.id)
        )
        return list(self._session.scalars(statement).unique())

    def update(
        self,
        car_id: int,
        *,
        price: float | None = None,
        mileage: int | None = None,
    ) -> CarRecord | None:
        car = self._session.get(CarRecord, car_id)
        if car is None:
            return None
        if price is not None and not math.isfinite(price):
            raise ValueError("Price must be finite")
        if price is not None:
            car.price = price
        if mileage is not None:
            car.mileage = mileage
        self._session.flush()
        return car

    def update_price(self, car_id: int, price: float) -> CarRecord | None:
        """Update only a car's price, preserving its mileage."""
        return self.update(car_id, price=price)

    def update_mileage(self, car_id: int, mileage: int) -> CarRecord | None:
        """Update only a car's mileage, preserving its price."""
        return self.update(car_id, mileage=mileage)

    def delete(self, car_id: int) -> bool:
        car = self._session.get(CarRecord, car_id)
        if car is None:
            return False
        self._session.delete(car)
        self._session.flush()
        return True

    def most_expensive(self) -> CarRecord | None:
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .order_by(CarRecord.price.desc(), CarRecord.id)
            .limit(1)
        )
        return self._session.scalar(statement)

    def average_price(self) -> float:
        result = self._session.scalar(select(func.avg(CarRecord.price)))
        return float(result) if result is not None else 0.0

    def lowest_mileage(self) -> CarRecord | None:
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .order_by(CarRecord.mileage, CarRecord.id)
            .limit(1)
        )
        return self._session.scalar(statement)

    @classmethod
    def _validate_car_data(
        cls,
        model: str,
        year: int,
        price: float,
        mileage: int,
        vin: str | None,
    ) -> None:
        if not model.strip():
            raise ValueError("Car model cannot be empty")
        if year < 1886:
            raise ValueError("Year must be 1886 or later")
        cls._validate_price(price)
        if mileage < 0:
            raise ValueError("Mileage cannot be negative")
        if vin is not None and not vin.strip():
            raise ValueError("VIN cannot be empty")

    @staticmethod
    def _validate_price(price: float) -> None:
        if not math.isfinite(price) or price < 0:
            raise ValueError("Price must be finite and non-negative")
