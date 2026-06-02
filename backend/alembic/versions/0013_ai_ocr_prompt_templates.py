"""ai_ocr_prompt_templates table

Revision ID: 0013_ai_ocr_prompt_templates
Revises: 0012_ai_ocr_prompts
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_ai_ocr_prompt_templates"
down_revision: Union[str, None] = "0012_ai_ocr_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_NAME = "기본 매뉴얼 OCR"
MIGRATED_NAME = "이전 설정 (마이그레이션)"


def upgrade() -> None:
    op.create_table(
        "ai_ocr_prompt_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_ocr_prompt_templates_name", "ai_ocr_prompt_templates", ["name"], unique=False)

    op.add_column("ai_ocr_settings", sa.Column("active_prompt_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_ocr_settings_active_prompt",
        "ai_ocr_settings",
        "ai_ocr_prompt_templates",
        ["active_prompt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    settings_row = connection.execute(
        sa.text(
            "SELECT system_prompt, user_prompt FROM ai_ocr_settings WHERE id = 1"
        )
    ).fetchone()

    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[2]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from services.article_from_image import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT

    default_id = connection.execute(
        sa.text(
            """
            INSERT INTO ai_ocr_prompt_templates (name, description, system_prompt, user_prompt, is_builtin)
            VALUES (:name, :desc, :sys, :user, true)
            RETURNING id
            """
        ),
        {
            "name": DEFAULT_NAME,
            "desc": "앱 기본 이미지→아티클 변환 프롬프트",
            "sys": DEFAULT_SYSTEM_PROMPT,
            "user": DEFAULT_USER_PROMPT,
        },
    ).scalar_one()

    active_id = default_id
    if settings_row:
        sys_custom = (settings_row[0] or "").strip()
        user_custom = (settings_row[1] or "").strip()
        if sys_custom or user_custom:
            migrated_id = connection.execute(
                sa.text(
                    """
                    INSERT INTO ai_ocr_prompt_templates (name, system_prompt, user_prompt, is_builtin)
                    VALUES (:name, :sys, :user, false)
                    RETURNING id
                    """
                ),
                {
                    "name": MIGRATED_NAME,
                    "sys": sys_custom or DEFAULT_SYSTEM_PROMPT,
                    "user": user_custom or DEFAULT_USER_PROMPT,
                },
            ).scalar_one()
            active_id = migrated_id

    connection.execute(
        sa.text("UPDATE ai_ocr_settings SET active_prompt_id = :pid WHERE id = 1"),
        {"pid": active_id},
    )

    op.drop_column("ai_ocr_settings", "user_prompt")
    op.drop_column("ai_ocr_settings", "system_prompt")


def downgrade() -> None:
    op.add_column("ai_ocr_settings", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column("ai_ocr_settings", sa.Column("user_prompt", sa.Text(), nullable=True))

    connection = op.get_bind()
    active = connection.execute(
        sa.text(
            """
            SELECT t.system_prompt, t.user_prompt
            FROM ai_ocr_settings s
            LEFT JOIN ai_ocr_prompt_templates t ON t.id = s.active_prompt_id
            WHERE s.id = 1
            """
        )
    ).fetchone()
    if active and (active[0] or active[1]):
        connection.execute(
            sa.text(
                "UPDATE ai_ocr_settings SET system_prompt = :sys, user_prompt = :user WHERE id = 1"
            ),
            {"sys": active[0], "user": active[1]},
        )

    op.drop_constraint("fk_ai_ocr_settings_active_prompt", "ai_ocr_settings", type_="foreignkey")
    op.drop_column("ai_ocr_settings", "active_prompt_id")
    op.drop_index("ix_ai_ocr_prompt_templates_name", table_name="ai_ocr_prompt_templates")
    op.drop_table("ai_ocr_prompt_templates")
