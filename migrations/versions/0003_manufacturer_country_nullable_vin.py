"""Add manufacturer country and allow cars without a VIN.

Revision ID: 0003_country_nullable_vin
Revises: 0002_unique_vin
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_country_nullable_vin"
down_revision = "0002_unique_vin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "manufacturers",
        sa.Column("country", sa.String(length=100), nullable=True),
    )
    op.get_bind().execute(
        sa.text("UPDATE manufacturers SET country = 'Unknown' WHERE country IS NULL")
    )
    with op.batch_alter_table("manufacturers") as batch_op:
        batch_op.alter_column(
            "country",
            existing_type=sa.String(length=100),
            nullable=False,
        )
    with op.batch_alter_table("cars") as batch_op:
        batch_op.alter_column(
            "vin",
            existing_type=sa.String(length=32),
            nullable=True,
        )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE cars SET vin = 'LEGACY-' || id WHERE vin IS NULL")
    )
    with op.batch_alter_table("cars") as batch_op:
        batch_op.alter_column(
            "vin",
            existing_type=sa.String(length=32),
            nullable=False,
        )
    with op.batch_alter_table("manufacturers") as batch_op:
        batch_op.drop_column("country")
