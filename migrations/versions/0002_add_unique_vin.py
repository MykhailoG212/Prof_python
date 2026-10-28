"""Add a required unique VIN to cars.

Revision ID: 0002_unique_vin
Revises: 0001_catalog
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_unique_vin"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("vin", sa.String(length=32), nullable=True))
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE cars SET vin = 'LEGACY-' || id"))
    with op.batch_alter_table("cars") as batch_op:
        batch_op.alter_column("vin", existing_type=sa.String(length=32), nullable=False)
        batch_op.create_unique_constraint("uq_cars_vin", ["vin"])


def downgrade() -> None:
    with op.batch_alter_table("cars") as batch_op:
        batch_op.drop_constraint("uq_cars_vin", type_="unique")
        batch_op.drop_column("vin")
