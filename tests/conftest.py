import pytest

from car_catalog.reliable.models import ProcessingConfig


@pytest.fixture(scope="session")
def processing_config() -> ProcessingConfig:
    return ProcessingConfig(
        minimum_year=1886,
        maximum_year=2026,
        minimum_price=0.0,
        maximum_price=1_000_000.0,
        invalid_record_policy="tolerant",
    )
