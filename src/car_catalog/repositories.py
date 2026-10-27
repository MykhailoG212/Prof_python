"""Універсальне in-memory сховище та конкретний репозиторій авто."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Generic, TypeVar

from car_catalog.models import Vehicle

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Контракт типізованого сховища сутностей."""

    @abstractmethod
    def add(self, item_id: int, item: T) -> None: ...

    @abstractmethod
    def get(self, item_id: int) -> T | None: ...

    @abstractmethod
    def all(self) -> Iterable[T]: ...


class InMemoryRepository(Repository[T]):
    """Generic repository з інкапсульованим індексом за ID."""

    def __init__(self) -> None:
        self._items: dict[int, T] = {}

    def add(self, item_id: int, item: T) -> None:
        if item_id <= 0:
            raise ValueError("ID має бути додатним")
        self._items[item_id] = item

    def get(self, item_id: int) -> T | None:
        return self._items.get(item_id)

    def all(self) -> Iterable[T]:
        return tuple(self._items.values())


class VehicleCatalog:
    """Колекція транспортних засобів, що композиційно використовує repository."""

    def __init__(self, repository: Repository[Vehicle] | None = None) -> None:
        self._repository: Repository[Vehicle] = repository or InMemoryRepository[Vehicle]()
        self._next_id = 1

    def add(self, vehicle: Vehicle) -> int:
        item_id = self._next_id
        self._repository.add(item_id, vehicle)
        self._next_id += 1
        return item_id

    def get(self, item_id: int) -> Vehicle | None:
        return self._repository.get(item_id)

    def all(self) -> tuple[Vehicle, ...]:
        return tuple(self._repository.all())

    def __len__(self) -> int:
        return sum(1 for _ in self._repository.all())

    def __iter__(self) -> Iterator[Vehicle]:
        return iter(self._repository.all())

    def __contains__(self, item_id: object) -> bool:
        return isinstance(item_id, int) and self._repository.get(item_id) is not None

    def __getitem__(self, item_id: int) -> Vehicle:
        vehicle = self._repository.get(item_id)
        if vehicle is None:
            raise KeyError(item_id)
        return vehicle
