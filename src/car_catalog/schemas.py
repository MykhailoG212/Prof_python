"""Pydantic schemas used by the HTTP API."""

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ManufacturerResponse(BaseModel):
    """Manufacturer fields included in car responses."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    country: str


class CarCreate(BaseModel):
    """Validated request body for creating a car."""

    manufacturer_id: int = Field(gt=0)
    model: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1886)
    price: float = Field(ge=0, allow_inf_nan=False)
    mileage: int = Field(ge=0)
    vin: str | None = Field(default=None, max_length=32)

    @field_validator("model")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Reject whitespace-only values and normalize surrounding spaces."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized

    @field_validator("vin")
    @classmethod
    def strip_optional_vin(cls, value: str | None) -> str | None:
        """Normalize a VIN when provided and reject whitespace-only values."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("VIN must not be empty when provided")
        return normalized


class CarUpdate(BaseModel):
    """Partial update request for mutable car fields."""

    price: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    mileage: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_at_least_one_value(self) -> Self:
        """Reject empty patches and explicit nulls for numeric fields."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if self.price is None and "price" in self.model_fields_set:
            raise ValueError("Price cannot be null")
        if self.mileage is None and "mileage" in self.model_fields_set:
            raise ValueError("Mileage cannot be null")
        return self


class CarResponse(BaseModel):
    """Car and manufacturer representation returned by the API."""

    model_config = {"from_attributes": True}

    id: int
    manufacturer_id: int
    model: str
    year: int
    price: float
    mileage: int
    vin: str | None
    manufacturer: ManufacturerResponse


class CarStatisticsResponse(BaseModel):
    """Catalog-wide statistics returned by the statistics endpoint."""

    model_config = {"from_attributes": True}

    average_price: float
    most_expensive_car: CarResponse | None
    lowest_mileage_car: CarResponse | None


class BatchCheckRequest(BaseModel):
    """External car identifiers to check against the configured upstream."""

    car_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("car_ids")
    @classmethod
    def require_positive_ids(cls, values: list[int]) -> list[int]:
        """Ensure upstream paths are constructed from positive identifiers."""
        if any(car_id <= 0 for car_id in values):
            raise ValueError("Car IDs must be positive")
        return values


class ExternalCarCheckResult(BaseModel):
    """Outcome for one external car check."""

    car_id: int
    success: bool
    status_code: int | None
    error: str | None = None


class BatchCheckResponse(BaseModel):
    """Results returned by the external batch-check endpoint."""

    results: list[ExternalCarCheckResult]
