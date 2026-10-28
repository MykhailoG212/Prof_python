"""Integration tests for the FastAPI car catalog endpoints."""

import asyncio

import httpx
import pytest

from car_catalog.external_api import ExternalCarApiClient
from car_catalog.persistence import CarRepository, Database, ManufacturerRepository

pytestmark = pytest.mark.asyncio


async def test_health_reports_status_and_environment(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["environment"], str)


def add_manufacturer(
    database: Database,
    name: str = "Toyota",
    country: str = "Unknown",
) -> int:
    """Create a manufacturer and return its primary key."""
    with database.session_factory.begin() as session:
        manufacturer = ManufacturerRepository(session).create(name, country)
        return manufacturer.id


def add_car(
    database: Database,
    manufacturer_id: int,
    *,
    model: str,
    year: int,
    price: float,
    mileage: int,
    vin: str,
) -> int:
    """Create a car through the existing persistence repository."""
    with database.session_factory.begin() as session:
        car = CarRepository(session).create(
            manufacturer_id=manufacturer_id,
            model=model,
            year=year,
            price=price,
            mileage=mileage,
            vin=vin,
        )
        return car.id


async def test_car_crud_and_not_found_responses(
    api_client: httpx.AsyncClient,
    api_database: Database,
) -> None:
    manufacturer_id = add_manufacturer(api_database, country="Japan")
    payload = {
        "manufacturer_id": manufacturer_id,
        "model": "Camry",
        "year": 2020,
        "price": 25_000,
        "mileage": 45_000,
        "vin": "VIN-API-001",
    }

    created = await api_client.post("/cars", json=payload)

    assert created.status_code == 201
    car = created.json()
    assert car["manufacturer"] == {
        "id": manufacturer_id,
        "name": "Toyota",
        "country": "Japan",
    }
    car_id = car["id"]
    duplicate = await api_client.post("/cars", json=payload)
    assert duplicate.status_code == 409
    assert (await api_client.get(f"/cars/{car_id}")).status_code == 200
    assert (await api_client.get("/cars/999")).status_code == 404

    updated = await api_client.patch(f"/cars/{car_id}", json={"price": 22_000})

    assert updated.status_code == 200
    assert updated.json()["price"] == 22_000
    assert updated.json()["mileage"] == 45_000
    assert (await api_client.delete(f"/cars/{car_id}")).status_code == 204
    assert (await api_client.get(f"/cars/{car_id}")).status_code == 404
    assert (await api_client.delete(f"/cars/{car_id}")).status_code == 404
    optional_vin_payload = payload.copy()
    optional_vin_payload.pop("vin")
    optional_vin_payload["model"] = "Prius"
    optional_vin = await api_client.post("/cars", json=optional_vin_payload)
    assert optional_vin.status_code == 201
    assert optional_vin.json()["vin"] is None


async def test_car_list_search_and_filters(
    api_client: httpx.AsyncClient,
    api_database: Database,
) -> None:
    toyota_id = add_manufacturer(api_database)
    honda_id = add_manufacturer(api_database, "Honda")
    add_car(
        api_database,
        toyota_id,
        model="Camry",
        year=2020,
        price=25_000,
        mileage=45_000,
        vin="VIN-API-002",
    )
    add_car(
        api_database,
        toyota_id,
        model="Corolla",
        year=2019,
        price=18_000,
        mileage=60_000,
        vin="VIN-API-003",
    )
    add_car(
        api_database,
        honda_id,
        model="Civic",
        year=2020,
        price=22_000,
        mileage=30_000,
        vin="VIN-API-004",
    )

    assert len((await api_client.get("/cars")).json()) == 3
    assert [car["model"] for car in (await api_client.get("/cars?search=toyota")).json()] == [
        "Camry",
        "Corolla",
    ]
    assert [car["model"] for car in (await api_client.get("/cars?search=vic")).json()] == ["Civic"]
    assert [car["model"] for car in (await api_client.get("/cars?year=2020")).json()] == [
        "Camry",
        "Civic",
    ]
    filtered = await api_client.get("/cars?min_price=20000&max_price=24000")
    assert [car["model"] for car in filtered.json()] == ["Civic"]
    assert (await api_client.get("/cars?min_price=30000&max_price=10000")).status_code == 422


async def test_validation_manufacturer_lookup_and_empty_patch(
    api_client: httpx.AsyncClient,
) -> None:
    invalid_price = await api_client.post(
        "/cars",
        json={
            "manufacturer_id": 1,
            "model": "Invalid",
            "year": 2020,
            "price": -1,
            "mileage": 0,
            "vin": "VIN-API-INVALID",
        },
    )
    missing_manufacturer = await api_client.post(
        "/cars",
        json={
            "manufacturer_id": 999,
            "model": "Missing",
            "year": 2020,
            "price": 1,
            "mileage": 0,
            "vin": "VIN-API-MISSING",
        },
    )

    assert invalid_price.status_code == 422
    assert missing_manufacturer.status_code == 404
    assert (await api_client.patch("/cars/1", json={})).status_code == 422
    assert (await api_client.patch("/cars/1", json={"price": None})).status_code == 422


async def test_manufacturer_cars_and_statistics(
    api_client: httpx.AsyncClient,
    api_database: Database,
) -> None:
    toyota_id = add_manufacturer(api_database)
    honda_id = add_manufacturer(api_database, "Honda")
    add_car(
        api_database,
        toyota_id,
        model="Camry",
        year=2020,
        price=25_000,
        mileage=45_000,
        vin="VIN-API-005",
    )
    add_car(
        api_database,
        honda_id,
        model="Civic",
        year=2021,
        price=30_000,
        mileage=10_000,
        vin="VIN-API-006",
    )

    manufacturer_cars = await api_client.get(f"/manufacturers/{toyota_id}/cars")
    assert manufacturer_cars.status_code == 200
    assert [car["model"] for car in manufacturer_cars.json()] == ["Camry"]
    assert (await api_client.get("/manufacturers/999/cars")).status_code == 404

    statistics = await api_client.get("/cars/statistics")
    assert statistics.status_code == 200
    assert statistics.json()["average_price"] == 27_500
    assert statistics.json()["most_expensive_car"]["model"] == "Civic"
    assert statistics.json()["lowest_mileage_car"]["model"] == "Civic"
    summary = await api_client.get("/cars/statistics/summary")
    assert summary.status_code == 200
    assert summary.json() == statistics.json()


async def test_batch_check_runs_external_async_pipeline(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post("/cars/batch-check", json={"car_ids": [10, 404]})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"car_id": 10, "success": True, "status_code": 200, "error": None},
        {
            "car_id": 404,
            "success": False,
            "status_code": 404,
            "error": "Upstream returned HTTP 404",
        },
    ]
    assert (await api_client.post("/cars/batch-check", json={"car_ids": []})).status_code == 422


async def test_external_client_retries_transient_server_errors() -> None:
    attempts = 0

    async def upstream_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        assert request.url.path == "/cars/1"
        attempts += 1
        await asyncio.sleep(0)
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200)

    client = ExternalCarApiClient(
        "https://upstream.test",
        max_attempts=2,
        retry_delay_seconds=0,
        transport=httpx.MockTransport(upstream_handler),
    )

    results = await client.check_cars([1])

    assert attempts == 2
    assert len(results) == 1
    assert results[0].success
    assert results[0].status_code == 200


@pytest.mark.asyncio
async def test_external_client_respects_concurrency_limit() -> None:
    active_requests = 0
    maximum_active_requests = 0
    request_lock = asyncio.Lock()

    async def upstream_handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_requests, maximum_active_requests
        assert request.url.path.startswith("/cars/")
        async with request_lock:
            active_requests += 1
            maximum_active_requests = max(maximum_active_requests, active_requests)
        await asyncio.sleep(0.01)
        async with request_lock:
            active_requests -= 1
        return httpx.Response(200)

    client = ExternalCarApiClient(
        "https://upstream.test",
        max_concurrency=2,
        transport=httpx.MockTransport(upstream_handler),
    )

    results = await client.check_cars([1, 2, 3, 4, 5])

    assert len(results) == 5
    assert maximum_active_requests == 2
