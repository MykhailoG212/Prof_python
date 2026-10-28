"""FastAPI application and REST endpoints for the car catalog."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from car_catalog.dependencies import get_catalog_service, get_external_client, get_session
from car_catalog.external_api import ExternalCarApiClient
from car_catalog.persistence import (
    CarCatalogDbService,
    CarRecord,
    CarRepository,
    Database,
    ManufacturerRecord,
    ManufacturerRepository,
)
from car_catalog.schemas import (
    BatchCheckRequest,
    BatchCheckResponse,
    CarCreate,
    CarResponse,
    CarStatisticsResponse,
    CarUpdate,
)


def create_app(database: Database | None = None) -> FastAPI:
    """Create the API application, optionally using an injected database."""
    application_database = database or Database()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        application_database.create_schema()
        try:
            yield
        finally:
            application_database.dispose()

    app = FastAPI(
        title="Car Catalog API",
        version="1.0.0",
        description="REST API for the persistent car catalog.",
        lifespan=lifespan,
    )
    app.state.database = application_database

    @app.get("/cars", response_model=list[CarResponse])
    def list_cars(
        session: Annotated[Session, Depends(get_session)],
        search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        year: Annotated[int | None, Query(ge=1886)] = None,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[CarRecord]:
        """List cars, optionally filtering by model, manufacturer, year, and price."""
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=422,
                detail="min_price must not exceed max_price",
            )
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .join(CarRecord.manufacturer)
        )
        if search is not None:
            search_term = search.strip()
            if not search_term:
                raise HTTPException(
                    status_code=422,
                    detail="search must not contain only whitespace",
                )
            statement = statement.where(
                or_(
                    CarRecord.model.ilike(f"%{search_term}%"),
                    ManufacturerRecord.name.ilike(f"%{search_term}%"),
                )
            )
        if year is not None:
            statement = statement.where(CarRecord.year == year)
        if min_price is not None:
            statement = statement.where(CarRecord.price >= min_price)
        if max_price is not None:
            statement = statement.where(CarRecord.price <= max_price)
        statement = statement.order_by(CarRecord.id).offset(offset).limit(limit)
        return list(session.scalars(statement).unique())

    @app.get("/cars/statistics", response_model=CarStatisticsResponse)
    def get_statistics(
        service: Annotated[CarCatalogDbService, Depends(get_catalog_service)],
    ) -> CarStatisticsResponse:
        """Return average price, most expensive car, and lowest-mileage car."""
        statistics = service.get_catalog_statistics()
        return CarStatisticsResponse.model_validate(statistics)

    @app.post(
        "/cars/batch-check",
        response_model=BatchCheckResponse,
        status_code=status.HTTP_200_OK,
    )
    async def batch_check(
        payload: BatchCheckRequest,
        client: Annotated[ExternalCarApiClient, Depends(get_external_client)],
    ) -> BatchCheckResponse:
        """Check car identifiers against the configured external API."""
        results = await client.check_cars(payload.car_ids)
        return BatchCheckResponse(results=results)

    @app.get("/cars/{car_id}", response_model=CarResponse)
    def get_car(
        car_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> CarRecord:
        """Return one car by its database identifier."""
        car = CarRepository(session).get_by_id(car_id)
        if car is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Car {car_id} was not found",
            )
        return car

    @app.post(
        "/cars",
        response_model=CarResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_car(
        payload: CarCreate,
        session: Annotated[Session, Depends(get_session)],
    ) -> CarRecord:
        """Create a car after validating its manufacturer and persisted values."""
        repository = CarRepository(session)
        try:
            car = repository.create(
                manufacturer_id=payload.manufacturer_id,
                model=payload.model,
                year=payload.year,
                price=payload.price,
                mileage=payload.mileage,
                vin=payload.vin,
            )
            session.commit()
        except LookupError as error:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A car with this VIN already exists",
            ) from error
        created_car = repository.get_by_id(car.id)
        if created_car is None:
            raise RuntimeError("Created car could not be reloaded")
        return created_car

    @app.patch("/cars/{car_id}", response_model=CarResponse)
    def update_car(
        car_id: int,
        payload: CarUpdate,
        session: Annotated[Session, Depends(get_session)],
    ) -> CarRecord:
        """Partially update a car's price and/or mileage."""
        repository = CarRepository(session)
        car = repository.update(
            car_id,
            price=payload.price,
            mileage=payload.mileage,
        )
        if car is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Car {car_id} was not found",
            )
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail="Updated car values violate database constraints",
            ) from error
        updated_car = repository.get_by_id(car_id)
        if updated_car is None:
            raise RuntimeError("Updated car could not be reloaded")
        return updated_car

    @app.delete("/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_car(
        car_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> Response:
        """Delete a car and return an empty 204 response."""
        if not CarRepository(session).delete(car_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Car {car_id} was not found",
            )
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/manufacturers/{manufacturer_id}/cars",
        response_model=list[CarResponse],
    )
    def list_manufacturer_cars(
        manufacturer_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> list[CarRecord]:
        """List cars for a manufacturer, returning 404 for an unknown manufacturer."""
        manufacturer = ManufacturerRepository(session).get_by_id(manufacturer_id)
        if manufacturer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manufacturer {manufacturer_id} was not found",
            )
        statement = (
            select(CarRecord)
            .options(joinedload(CarRecord.manufacturer))
            .where(CarRecord.manufacturer_id == manufacturer_id)
            .order_by(CarRecord.id)
        )
        return list(session.scalars(statement).unique())

    return app


app = create_app()
