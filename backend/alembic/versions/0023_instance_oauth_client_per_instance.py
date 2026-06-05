"""per-instance Zendesk OAuth client credentials

Revision ID: 0023_instance_oauth_client
Revises: 0022_instance_oauth_tokens
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_instance_oauth_client"
down_revision: Union[str, None] = "0022_instance_oauth_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "instances",
        sa.Column("oauth_client_id", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "instances",
        sa.Column("oauth_client_secret", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "instances",
        sa.Column("oauth_redirect_uri", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "instances",
        sa.Column("oauth_scopes", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("instances", "oauth_scopes")
    op.drop_column("instances", "oauth_redirect_uri")
    op.drop_column("instances", "oauth_client_secret")
    op.drop_column("instances", "oauth_client_id")
