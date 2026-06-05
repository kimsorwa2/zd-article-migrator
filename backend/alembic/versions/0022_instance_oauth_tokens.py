"""instance oauth tokens (API token → OAuth)

Revision ID: 0022_instance_oauth_tokens
Revises: 0021_ai_ocr_preprocess_flag
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_instance_oauth_tokens"
down_revision: Union[str, None] = "0021_ai_ocr_preprocess_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 기존 api_token 인스턴스는 OAuth 재연결 전까지 빈 문자열로 둔다.
    op.add_column(
        "instances",
        sa.Column("oauth_access_token", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "instances",
        sa.Column("oauth_refresh_token", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_column("instances", "api_token")


def downgrade() -> None:
    op.add_column("instances", sa.Column("api_token", sa.String(length=255), nullable=True))
    op.drop_column("instances", "oauth_refresh_token")
    op.drop_column("instances", "oauth_access_token")
    op.alter_column("instances", "api_token", nullable=False, server_default="")
