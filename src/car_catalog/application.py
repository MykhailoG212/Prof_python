"""Application service: use cases каталогу з DI та залежністю від Protocol."""

from car_catalog.criteria import BrandModelCriteria, YearCriteria
from car_catalog.dto import VehicleData
from car_catalog.models import ElectricCar, Vehicle
from car_catalog.protocols import SearchCriteria, VehicleRepository


class VehicleCatalogService:
    """Виконує сценарії каталогу, отримуючи repository ззовні."""

    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository
        self._next_id = 1

    def add(self, vehicle: Vehicle) -> int:
        item_id = self._next_id
        self._repository.add(item_id, vehicle)
        self._next_id += 1
        return item_id

    def search(self, criteria: SearchCriteria[Vehicle]) -> list[Vehicle]:
        return [vehicle for vehicle in self._repository.all() if criteria.matches(vehicle)]

    def search_by_brand_or_model(self, brand: str | None = None, model: str | None = None) -> list[Vehicle]:
        return self.search(BrandModelCriteria(brand=brand, model=model))

    def filter_by_year(self, year: int) -> list[Vehicle]:
        return self.search(YearCriteria(year))

    def most_expensive(self) -> Vehicle | None:
        return max(self._repository.all(), key=lambda vehicle: vehicle.price, default=None)

    def average_price(self) -> float:
        vehicles = tuple(self._repository.all())
        return sum(vehicle.price for vehicle in vehicles) / len(vehicles) if vehicles else 0.0

    def lowest_mileage(self) -> Vehicle | None:
        return min(self._repository.all(), key=lambda vehicle: vehicle.mileage, default=None)

    def to_data(self, item_id: int, vehicle: Vehicle) -> VehicleData:
        return {
            "id": item_id,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "year": vehicle.year,
            "price": vehicle.price,
            "mileage": vehicle.mileage,
            "kind": "electric" if isinstance(vehicle, ElectricCar) else "car",
        }

