from collections.abc import AsyncIterator, Callable, Generator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import URL

from car_catalog.api import create_app
from car_catalog.dependencies import get_external_client
from car_catalog.external_api import ExternalCarApiClient
from car_catalog.models import Car
from car_catalog.persistence import Database
from car_catalog.reliable.models import ProcessingConfig


@pytest.fixture
def api_database(tmp_path: Path) -> Generator[Database, None, None]:
    """Provide an isolated SQLite database for one API test."""
    database = Database(URL.create("sqlite", database=str(tmp_path / "api-test.db")))
    yield database
    database.dispose()


@pytest_asyncio.fixture
async def api_client(api_database: Database) -> AsyncIterator[httpx.AsyncClient]:
    """Start an API app with a deterministic mock upstream."""
    async def upstream_handler(request: httpx.Request) -> httpx.Response:
        car_id = int(request.url.path.rsplit("/", maxsplit=1)[-1])
        return httpx.Response(200 if car_id != 404 else 404)

    app = create_app(api_database)
    app.dependency_overrides[get_external_client] = lambda: ExternalCarApiClient(
        "https://upstream.test",
        transport=httpx.MockTransport(upstream_handler),
    )
    try:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def car_factory() -> Callable[..., Car]:
    def create_car(
        *,
        brand: str = "Toyota",
        model: str = "Camry",
        year: int = 2020,
        price: float = 25_000.0,
        mileage: int = 45_000,
    ) -> Car:
        return Car(brand, model, year, price, mileage)

    return create_car


@pytest.fixture(scope="session")
def processing_config() -> ProcessingConfig:
    return ProcessingConfig(
        minimum_year=1886,
        maximum_year=2026,
        minimum_price=0.0,
        maximum_price=1_000_000.0,
        invalid_record_policy="tolerant",
    )
