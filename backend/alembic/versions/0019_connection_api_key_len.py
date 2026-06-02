"""ai_ocr_connections.api_key 길이 확장 (Bedrock 단기 API 키 1000자+)

Revision ID: 0019_connection_api_key_len
Revises: 0018_ai_ocr_connections
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_connection_api_key_len"
down_revision: Union[str, None] = "0018_ai_ocr_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_ocr_connections",
        "api_key",
        existing_type=sa.String(length=512),
        type_=sa.String(length=4096),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "ai_ocr_connections",
        "api_key",
        existing_type=sa.String(length=4096),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
