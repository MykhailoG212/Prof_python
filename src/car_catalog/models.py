"""Типізована об'єктна модель каталогу автомобілів (ЛР4)."""

import math
from abc import ABC
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class VehicleSpecification:
    """Незмінні технічні характеристики транспортного засобу."""

    fuel_type: str
    transmission: str
    body_style: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.fuel_type, self.transmission, self.body_style)):
            raise ValueError("Характеристики транспортного засобу не можуть бути порожніми")


@dataclass(slots=True, frozen=True)
class Vehicle(ABC):
    """Базова сутність каталогу; конкретний транспорт має ціну та характеристики."""

    brand: str
    model: str
    year: int
    price: float
    mileage: int
    specification: VehicleSpecification

    def __post_init__(self) -> None:
        if not self.brand.strip() or not self.model.strip():
            raise ValueError("Марка та модель не можуть бути порожніми")
        if self.year < 1886:
            raise ValueError(f"Некоректний рік випуску: {self.year}")
        if not math.isfinite(self.price) or self.price < 0:
            raise ValueError("Ціна має бути скінченною та невід'ємною")
        if self.mileage < 0:
            raise ValueError("Пробіг не може бути від'ємним")

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.year}) — ${self.price:,.2f}"


@dataclass(slots=True, frozen=True)
class Car(Vehicle):
    """Модель даних автомобіля.

    Атрибути:
        brand: Марка автомобіля.
        model: Модель автомобіля.
        year: Рік випуску (>= 1886).
        price: Ціна в USD (>= 0).
        mileage: Пробіг у кілометрах (>= 0).
    """

    specification: VehicleSpecification = VehicleSpecification("Бензин", "Автоматична", "Седан")


@dataclass(slots=True, frozen=True)
class ElectricCar(Car):
    """Автомобіль з електричним приводом; запас ходу задається в кілометрах."""

    range_km: int = 0

    def __post_init__(self) -> None:
        super(ElectricCar, self).__post_init__()
        if self.range_km <= 0:
            raise ValueError("Запас ходу електромобіля має бути додатним")
        if self.specification.fuel_type.casefold() not in {"електро", "electric"}:
            raise ValueError("Для ElectricCar тип пального має бути 'Електро'")
