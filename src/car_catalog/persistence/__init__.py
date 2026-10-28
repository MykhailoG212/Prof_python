"""SQLite persistence layer for the car catalog."""

from car_catalog.persistence.database import Database
from car_catalog.persistence.models import Base, CarRecord, ManufacturerRecord
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository
from car_catalog.persistence.services import CarCatalogService

__all__ = [
    "Base",
    "CarCatalogService",
    "CarRecord",
    "CarRepository",
    "Database",
    "ManufacturerRecord",
    "ManufacturerRepository",
]
