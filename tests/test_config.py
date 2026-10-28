"""Tests for environment-backed application settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import URL

from car_catalog.config import Settings, get_settings
from car_catalog.persistence import Database


def test_settings_load_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/catalog.db")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("PORT", "8123")
    get_settings.cache_clear()

    try:
        settings = get_settings()

        assert settings.database_url == "sqlite:////tmp/catalog.db"
        assert settings.environment == "testing"
        assert settings.log_level == "DEBUG"
        assert settings.port == 8123
    finally:
        get_settings.cache_clear()


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, LOG_LEVEL="TRACE")


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, PORT=70000)


def test_absolute_sqlite_path_creates_parent_and_enables_foreign_keys(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "data" / "catalog.db"
    database = Database(URL.create("sqlite", database=str(database_path)))

    try:
        assert database_path.parent.is_dir()
        with database.engine.connect() as connection:
            foreign_keys_enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        assert foreign_keys_enabled == 1
    finally:
        database.dispose()
