import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from car_catalog.application import VehicleCatalogService
from car_catalog.models import Car
from car_catalog.protocols import VehicleRepository


def test_search_uses_repository_result_and_checks_interaction() -> None:
    repository = MagicMock(spec=VehicleRepository)
    matching = Car("Tesla", "Model 3", 2023, 41_000.0, 12_000)
    repository.all.return_value = [
        matching,
        Car("Toyota", "Camry", 2020, 25_000.0, 45_000),
    ]
    service = VehicleCatalogService(repository)

    assert service.search_by_brand_or_model(brand="tesla") == [matching]
    repository.all.assert_called_once_with()
    repository.add.assert_not_called()


def test_failed_repository_add_preserves_next_id_for_retry(
    car_factory: Callable[..., Car],
) -> None:
    repository = Mock(spec=VehicleRepository)
    repository.add.side_effect = OSError("storage unavailable")
    service = VehicleCatalogService(repository)
    vehicle = car_factory()

    with pytest.raises(OSError, match="storage unavailable"):
        service.add(vehicle)

    repository.add.assert_called_once_with(1, vehicle)
    repository.add.side_effect = None
    assert service.add(vehicle) == 1
    assert repository.add.call_count == 2


def test_async_add_awaits_thread_offload_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
    car_factory: Callable[..., Car],
) -> None:
    repository = Mock(spec=VehicleRepository)
    service = VehicleCatalogService(repository)
    vehicle = car_factory()
    thread_offload = AsyncMock(return_value=7)
    monkeypatch.setattr("car_catalog.application.asyncio.to_thread", thread_offload)

    assert asyncio.run(service.add_async(vehicle)) == 7
    thread_offload.assert_awaited_once_with(service.add, vehicle)
    repository.add.assert_not_called()


def test_async_add_propagates_repository_failure(
    monkeypatch: pytest.MonkeyPatch,
    car_factory: Callable[..., Car],
) -> None:
    repository = Mock(spec=VehicleRepository)
    service = VehicleCatalogService(repository)
    vehicle = car_factory()
    thread_offload = AsyncMock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr("car_catalog.application.asyncio.to_thread", thread_offload)

    with pytest.raises(OSError, match="storage unavailable"):
        asyncio.run(service.add_async(vehicle))

    thread_offload.assert_awaited_once_with(service.add, vehicle)


def test_concurrent_async_adds_allocate_unique_ids(
    car_factory: Callable[..., Car],
) -> None:
    repository = Mock(spec=VehicleRepository)
    service = VehicleCatalogService(repository)
    vehicles = [car_factory(model=f"Model {index}") for index in range(20)]

    async def add_all() -> list[int]:
        return await asyncio.gather(*(service.add_async(vehicle) for vehicle in vehicles))

    assert sorted(asyncio.run(add_all())) == list(range(1, 21))
    assert sorted(call.args[0] for call in repository.add.call_args_list) == list(range(1, 21))
