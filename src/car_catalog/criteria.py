"""Реалізації критеріїв пошуку каталогу."""

from dataclasses import dataclass

from car_catalog.models import Vehicle


@dataclass(frozen=True, slots=True)
class BrandModelCriteria:
    brand: str | None = None
    model: str | None = None

    def matches(self, item: Vehicle, /) -> bool:
        return (
            (self.brand is None or item.brand.casefold() == self.brand.strip().casefold())
            and (self.model is None or item.model.casefold() == self.model.strip().casefold())
        )


@dataclass(frozen=True, slots=True)
class YearCriteria:
    year: int

    def matches(self, item: Vehicle, /) -> bool:
        return item.year == self.year
