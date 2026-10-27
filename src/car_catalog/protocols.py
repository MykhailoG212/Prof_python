"""Абстракції для пошуку та збереження каталогу."""

from collections.abc import Iterable
from typing import Protocol, TypeVar, runtime_checkable

from car_catalog.models import Vehicle

T_contra = TypeVar("T_contra", contravariant=True)


@runtime_checkable
class SearchCriteria(Protocol[T_contra]):
    """Structural interface критерію пошуку."""

    def matches(self, item: T_contra, /) -> bool: ...


class VehicleRepository(Protocol):
    """Мінімальний інтерфейс сховища, потрібний сервісу каталогу."""

    def add(self, item_id: int, item: Vehicle) -> None: ...

    def get(self, item_id: int) -> Vehicle | None: ...

    def all(self) -> Iterable[Vehicle]: ...

