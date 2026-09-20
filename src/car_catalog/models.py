from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Car:
    """Модель даних автомобіля.

    Атрибути:
        make: Марка автомобіля.
        model: Модель автомобіля.
        year: Рік випуску (>= 1886).
        price: Ціна в USD (>= 0).
        mileage: Пробіг у кілометрах (>= 0).
    """

    make: str
    model: str
    year: int
    price: float
    mileage: int

    def __post_init__(self) -> None:
        if self.year < 1886:
            raise ValueError(f"Некоректний рік випуску: {self.year}")
        if self.price < 0:
            raise ValueError("Ціна не може бути від'ємною")
        if self.mileage < 0:
            raise ValueError("Пробіг не може бути від'ємним")

    @property
    def display_name(self) -> str:
        return f"{self.make} {self.model} ({self.year})"
