import pytest

from car_catalog.reliable.exceptions import RecordValidationError
from car_catalog.reliable.importers import parse_vehicle
from car_catalog.reliable.models import ProcessingConfig, Vehicle


@pytest.mark.parametrize(
    ("year", "price"),
    [(1886, "0"), (2026, "1000000")],
    ids=["minimum-boundary", "maximum-boundary"],
)
def test_parse_vehicle_accepts_inclusive_configuration_boundaries(
    processing_config: ProcessingConfig,
    year: int,
    price: str,
) -> None:
    vehicle = parse_vehicle(
        {
            "vehicle_id": "1",
            "brand": "Toyota",
            "model": "Camry",
            "year": str(year),
            "price": price,
            "mileage": "0",
        },
        line_number=2,
        config=processing_config,
    )

    assert vehicle == Vehicle(1, "Toyota", "Camry", year, float(price), 0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("year", "1885", "year is outside configured range"),
        ("year", "2027", "year is outside configured range"),
        ("price", "-0.01", "price must be non-negative"),
        ("price", "1000000.01", "price is outside configured range"),
        ("price", "nan", "price is outside configured range"),
        ("mileage", "-1", "mileage must be non-negative"),
    ],
)
def test_parse_vehicle_rejects_values_outside_boundaries(
    processing_config: ProcessingConfig,
    field: str,
    value: str,
    message: str,
) -> None:
    row = {
        "vehicle_id": "1",
        "brand": "Toyota",
        "model": "Camry",
        "year": "2020",
        "price": "25000",
        "mileage": "10000",
    }
    row[field] = value

    with pytest.raises(RecordValidationError, match=message):
        parse_vehicle(row, line_number=2, config=processing_config)
