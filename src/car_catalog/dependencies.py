"""FastAPI dependencies for database and upstream service access."""

from collections.abc import Generator
from typing import cast
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from car_catalog.config import get_settings
from car_catalog.external_api import ExternalCarApiClient
from car_catalog.persistence import CarCatalogDbService, Database


def get_session(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""
    database = cast(Database, request.app.state.database)
    with database.session_factory() as session:
        yield session


def get_catalog_service(request: Request) -> CarCatalogDbService:
    """Build the catalog service using the application's session factory."""
    database = cast(Database, request.app.state.database)
    return CarCatalogDbService(database.session_factory)


def get_external_client() -> ExternalCarApiClient:
    """Create an upstream client from an operator-configured base URL."""
    base_url = get_settings().external_api_url
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External car API is not configured",
        )
    parsed_url = urlsplit(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAR_CATALOG_EXTERNAL_API_URL must be an absolute HTTP(S) URL",
        )
    if parsed_url.username is not None or parsed_url.password is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External API URL must not contain credentials",
        )
    return ExternalCarApiClient(base_url)
