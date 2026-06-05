"""Client Credentials access token 만료 시각 컬럼

Revision ID: 0024_oauth_token_expires
Revises: 0023_instance_oauth_client
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_oauth_token_expires"
down_revision: Union[str, None] = "0023_instance_oauth_client"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "instances",
        sa.Column("oauth_token_expires_at", sa.String(length=32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("instances", "oauth_token_expires_at")
