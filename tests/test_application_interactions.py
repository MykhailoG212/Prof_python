from collections.abc import Callable
from unittest.mock import MagicMock, Mock

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
