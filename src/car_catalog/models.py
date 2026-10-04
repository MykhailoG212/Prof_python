import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Car:
    """Модель даних автомобіля.

    Атрибути:
        brand: Марка автомобіля.
        model: Модель автомобіля.
        year: Рік випуску (>= 1886).
        price: Ціна в USD (>= 0).
        mileage: Пробіг у кілометрах (>= 0).
    """

    brand: str
    model: str
    year: int
    price: float
    mileage: int

    def __post_init__(self) -> None:
        if not self.brand.strip():
            raise ValueError("Марка автомобіля не може бути порожньою")
        if not self.model.strip():
            raise ValueError("Модель автомобіля не може бути порожньою")
        if self.year < 1886:
            raise ValueError(f"Некоректний рік випуску: {self.year}")
        if not math.isfinite(self.price) or self.price < 0:
            raise ValueError("Ціна не може бути від'ємною")
        if self.mileage < 0:
            raise ValueError("Пробіг не може бути від'ємним")

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"
