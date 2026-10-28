"""SQLAlchemy models for manufacturers and their cars."""

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for persistence models."""


class ManufacturerRecord(Base):
    """A car manufacturer with its catalog entries."""

    __tablename__ = "manufacturers"
    __table_args__ = (UniqueConstraint("name", name="uq_manufacturers_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cars: Mapped[list["CarRecord"]] = relationship(
        back_populates="manufacturer",
        passive_deletes="all",
    )


class CarRecord(Base):
    """A persisted car belonging to one manufacturer."""

    __tablename__ = "cars"
    __table_args__ = (
        CheckConstraint("year >= 1886", name="ck_cars_year"),
        CheckConstraint("price >= 0", name="ck_cars_price"),
        CheckConstraint("mileage >= 0", name="ck_cars_mileage"),
        CheckConstraint("length(trim(model)) > 0", name="ck_cars_model"),
        UniqueConstraint("vin", name="uq_cars_vin"),
        Index("ix_cars_manufacturer_year", "manufacturer_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer: Mapped[ManufacturerRecord] = relationship(back_populates="cars")
