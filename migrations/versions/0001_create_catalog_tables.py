"""Create manufacturer and car tables.

Revision ID: 0001_catalog
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("name", name="uq_manufacturers_name"),
    )
    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manufacturer_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("mileage", sa.Integer(), nullable=False),
        sa.CheckConstraint("year >= 1886", name="ck_cars_year"),
        sa.CheckConstraint("price >= 0", name="ck_cars_price"),
        sa.CheckConstraint("mileage >= 0", name="ck_cars_mileage"),
        sa.CheckConstraint("length(trim(model)) > 0", name="ck_cars_model"),
        sa.ForeignKeyConstraint(
            ["manufacturer_id"],
            ["manufacturers.id"],
            name="fk_cars_manufacturer_id_manufacturers",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_cars_manufacturer_year", "cars", ["manufacturer_id", "year"])


def downgrade() -> None:
    op.drop_index("ix_cars_manufacturer_year", table_name="cars")
    op.drop_table("cars")
    op.drop_table("manufacturers")
