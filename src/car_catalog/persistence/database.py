"""Database engine and session configuration."""

import sqlite3
from pathlib import Path

from sqlalchemy import URL, create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from car_catalog.config import get_settings


class Database:
    """Owns the engine and transaction-ready SQLAlchemy session factory."""

    def __init__(self, url: str | URL | None = None) -> None:
        database_url = url if url is not None else get_settings().database_url
        parsed_url = make_url(database_url)
        if parsed_url.get_backend_name() == "sqlite":
            sqlite_path = parsed_url.database
            if sqlite_path and sqlite_path != ":memory:" and not sqlite_path.startswith("file:"):
                Path(sqlite_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        connect_args = (
            {"check_same_thread": False} if str(database_url).startswith("sqlite") else {}
        )
        self.engine: Engine = create_engine(database_url, connect_args=connect_args)
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    @staticmethod
    def _enable_sqlite_foreign_keys(
        connection: sqlite3.Connection,
        _: object,
    ) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    def create_schema(self) -> None:
        """Create missing tables for a new database."""
        from car_catalog.persistence.models import Base

        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        """Close all pooled database connections."""
        self.engine.dispose()
