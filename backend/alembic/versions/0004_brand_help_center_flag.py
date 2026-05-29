"""add brand help center flag

Revision ID: 0004_brand_help_center_flag
Revises: 0003_external_ids_bigint
Create Date: 2026-05-28 19:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_brand_help_center_flag"
down_revision: Union[str, None] = "0003_external_ids_bigint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "brands",
        sa.Column("has_help_center", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("brands", "has_help_center")
