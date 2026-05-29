"""make instance name nullable

Revision ID: 0002_instance_name_nullable
Revises: 0001_initial_schema
Create Date: 2026-05-28 18:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_instance_name_nullable"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("instances", "name", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("instances", "name", existing_type=sa.String(length=255), nullable=False)
