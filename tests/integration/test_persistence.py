"""Integration tests for the SQLite persistence layer and Alembic migrations."""

import sqlite3
from collections.abc import Generator
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, select
from sqlalchemy.exc import IntegrityError

from car_catalog.persistence import (
    CarCatalogService,
    CarRecord,
    CarRepository,
    Database,
    ManufacturerRepository,
)
from car_catalog.persistence.dbapi import search_cars_by_manufacturer

pytestmark = pytest.mark.integration


@pytest.fixture
def database(tmp_path: Path) -> Generator[Database, None, None]:
    instance = Database(URL.create("sqlite", database=str(tmp_path / "catalog.db")))
    instance.create_schema()
    yield instance
    instance.dispose()


def add_manufacturer(database: Database, name: str = "Toyota") -> int:
    with database.session_factory.begin() as session:
        manufacturer = ManufacturerRepository(session).create(name)
        return manufacturer.id


def add_car(
    database: Database,
    manufacturer_id: int,
    *,
    model: str = "Camry",
    year: int = 2020,
    price: float = 25_000,
    mileage: int = 45_000,
    vin: str = "VIN-TOYOTA-001",
) -> int:
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


def test_manufacturer_crud_and_car_relationship(database: Database) -> None:
    with database.session_factory.begin() as session:
        manufacturers = ManufacturerRepository(session)
        manufacturer = manufacturers.create(" Toyota ")
        assert manufacturer.name == "Toyota"
        assert manufacturers.get_by_id(manufacturer.id) is manufacturer
        assert manufacturers.get_by_name("toyota") is manufacturer
        assert manufacturers.list_all() == [manufacturer]

        cars = CarRepository(session)
        car = cars.create(
            manufacturer_id=manufacturer.id,
            model="Camry",
            year=2020,
            price=25_000,
            mileage=45_000,
            vin="VIN-TOYOTA-001",
        )
        cascaded_car = cars.create(
            manufacturer_id=manufacturer.id,
            model="Corolla",
            year=2019,
            price=18_000,
            mileage=60_000,
            vin="VIN-TOYOTA-002",
        )
        assert car.manufacturer is manufacturer
        assert {related_car.id for related_car in car.manufacturer.cars} == {car.id, cascaded_car.id}
        assert cars.get_by_id(car.id) is car
        assert cars.get_by_vin(car.vin) is car

        assert manufacturers.update(manufacturer.id, "Toyota Motors") is manufacturer
        assert cars.update(car.id, price=24_000, mileage=46_000) is car
        assert (car.price, car.mileage) == (24_000, 46_000)
        assert cars.delete(car.id)
        assert cars.get_by_id(car.id) is None
        assert not cars.delete(car.id)
        assert manufacturers.delete(manufacturer.id)
        assert manufacturers.get_by_id(manufacturer.id) is None
        assert not manufacturers.delete(manufacturer.id)
        assert cars.get_by_id(cascaded_car.id) is None


def test_car_year_filter_aggregates_and_manufacturer_search(database: Database) -> None:
    toyota_id = add_manufacturer(database)
    honda_id = add_manufacturer(database, "Honda")
    first_id = add_car(database, toyota_id, vin="VIN-TOYOTA-001")
    add_car(database, toyota_id, model="Corolla", year=2019, price=18_000, mileage=60_000, vin="VIN-TOYOTA-002")
    add_car(database, honda_id, model="Civic", year=2020, price=22_000, mileage=30_000, vin="VIN-HONDA-001")

    with database.session_factory() as session:
        repository = CarRepository(session)
        assert [car.id for car in repository.filter_by_year(2020)] == [first_id, 3]
        assert [car.model for car in repository.find_by_manufacturer("toyota")] == ["Camry", "Corolla"]
        assert repository.most_expensive() is not None
        assert repository.most_expensive().model == "Camry"
        assert repository.average_price() == pytest.approx((25_000 + 18_000 + 22_000) / 3)
        assert repository.lowest_mileage() is not None
        assert repository.lowest_mileage().model == "Civic"
        assert len(repository.list_all()) == 3


def test_parameterized_dbapi_search(database: Database) -> None:
    manufacturer_id = add_manufacturer(database)
    add_car(database, manufacturer_id)

    with closing(sqlite3.connect(database.engine.url.database)) as connection:
        found = search_cars_by_manufacturer(connection, "toyota")
        injection_attempt = search_cars_by_manufacturer(connection, "' OR 1=1 --")

    assert len(found) == 1
    assert found[0][1:3] == ("Toyota", "Camry")
    assert injection_attempt == []


def test_bulk_price_update_commits_all_changes(database: Database) -> None:
    manufacturer_id = add_manufacturer(database)
    first_id = add_car(database, manufacturer_id, vin="VIN-TOYOTA-001")
    second_id = add_car(database, manufacturer_id, model="Corolla", vin="VIN-TOYOTA-002")

    service = CarCatalogService(database.session_factory)
    assert service.update_prices_for_manufacturer(manufacturer_id, {first_id: 20_000, second_id: 21_000}) == 2

    with database.session_factory() as session:
        cars = session.scalars(select(CarRecord).order_by(CarRecord.id)).all()
    assert [car.price for car in cars] == [20_000, 21_000]


def test_bulk_price_update_rolls_back_on_invalid_price(database: Database) -> None:
    manufacturer_id = add_manufacturer(database)
    first_id = add_car(database, manufacturer_id, vin="VIN-TOYOTA-001")
    second_id = add_car(database, manufacturer_id, model="Corolla", vin="VIN-TOYOTA-002")
    service = CarCatalogService(database.session_factory)

    with pytest.raises(ValueError, match="finite and non-negative"):
        service.update_prices_for_manufacturer(manufacturer_id, {first_id: 20_000, second_id: float("nan")})

    with database.session_factory() as session:
        cars = session.scalars(select(CarRecord).order_by(CarRecord.id)).all()
    assert [car.price for car in cars] == [25_000, 25_000]


def test_foreign_key_vin_uniqueness_and_repository_validation(database: Database) -> None:
    manufacturer_id = add_manufacturer(database)
    add_car(database, manufacturer_id)

    with pytest.raises(IntegrityError):
        with database.session_factory.begin() as session:
            CarRepository(session).create(
                manufacturer_id=manufacturer_id,
                model="Corolla",
                year=2021,
                price=20_000,
                mileage=10_000,
                vin="VIN-TOYOTA-001",
            )

    with database.session_factory.begin() as session:
        repository = CarRepository(session)
        with pytest.raises(LookupError, match="does not exist"):
            repository.create(
                manufacturer_id=999,
                model="Civic",
                year=2021,
                price=20_000,
                mileage=10_000,
                vin="VIN-HONDA-001",
            )
        with pytest.raises(ValueError, match="Year"):
            repository.create(
                manufacturer_id=manufacturer_id,
                model="Civic",
                year=1800,
                price=20_000,
                mileage=10_000,
                vin="VIN-HONDA-001",
            )
        assert repository.update(999, price=1) is None


def test_alembic_migration_adds_unique_vin_and_backfills_existing_cars(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    url = URL.create("sqlite", database=str(database_path))
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option(
        "sqlalchemy.url",
        url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    command.upgrade(alembic_config, "0001_catalog")
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute("INSERT INTO manufacturers (name) VALUES (?)", ("Toyota",))
            connection.execute(
                """
                INSERT INTO cars (manufacturer_id, model, year, price, mileage)
                VALUES (?, ?, ?, ?, ?)
                """,
                (1, "Camry", 2020, 25_000, 45_000),
            )

    command.upgrade(alembic_config, "head")

    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("SELECT vin FROM cars WHERE id = 1").fetchone() == ("LEGACY-1",)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO cars (manufacturer_id, model, year, price, mileage, vin)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "Corolla", 2021, 20_000, 10_000, "LEGACY-1"),
            )
