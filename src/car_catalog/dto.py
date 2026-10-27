"""TypedDict контракт для JSON-подібного представлення авто."""

from typing import TypedDict


class VehicleData(TypedDict):
    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int
    kind: str

