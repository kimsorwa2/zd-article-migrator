"""ai_ocr_connections.prompt_template_id — 연동별 OCR 프롬프트

Revision ID: 0020_ai_ocr_connection_prompt
Revises: 0019_connection_api_key_len
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_ai_ocr_connection_prompt"
down_revision: Union[str, None] = "0019_connection_api_key_len"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_ocr_connections",
        sa.Column("prompt_template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_ocr_connections_prompt_template",
        "ai_ocr_connections",
        "ai_ocr_prompt_templates",
        ["prompt_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # 기존 연동은 전역 active_prompt_id(없으면 builtin)로 채운다.
    op.execute(
        sa.text(
            """
            UPDATE ai_ocr_connections c
            SET prompt_template_id = COALESCE(
                (SELECT s.active_prompt_id FROM ai_ocr_settings s WHERE s.id = 1),
                (SELECT t.id FROM ai_ocr_prompt_templates t WHERE t.is_builtin = true LIMIT 1)
            )
            WHERE c.prompt_template_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_ai_ocr_connections_prompt_template", "ai_ocr_connections", type_="foreignkey")
    op.drop_column("ai_ocr_connections", "prompt_template_id")
