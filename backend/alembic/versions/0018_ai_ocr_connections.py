"""ai_ocr_connections — 다중 AI 연동 프로필

Revision ID: 0018_ai_ocr_connections
Revises: 0017_ai_ocr_history_compare
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_ai_ocr_connections"
down_revision: Union[str, None] = "0017_ai_ocr_history_compare"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_ocr_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("account", sa.String(length=255), nullable=True),
        sa.Column("api_key", sa.String(length=512), nullable=True),
        sa.Column("api_secret", sa.String(length=512), nullable=True),
        sa.Column("aws_region", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_ocr_connections_provider", "ai_ocr_connections", ["provider"])

    op.add_column("ai_ocr_settings", sa.Column("active_connection_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_ocr_settings_active_connection",
        "ai_ocr_settings",
        "ai_ocr_connections",
        ["active_connection_id"],
        ["id"],
        ondelete="SET NULL",
    )

    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            "SELECT active_provider, gemini_account, gemini_api_key, gemini_model, "
            "openai_account, openai_api_key, openai_model FROM ai_ocr_settings WHERE id = 1"
        )
    ).fetchone()
    if row is None:
        return

    active_provider = row[0] or "gemini"
    active_connection_id = None

    if row[2]:
        gemini_id = conn.execute(
            sa.text(
                "INSERT INTO ai_ocr_connections (provider, model, account, api_key) "
                "VALUES ('gemini', :model, :account, :api_key) RETURNING id"
            ),
            {"model": row[3] or "gemini-2.5-pro", "account": row[1], "api_key": row[2]},
        ).scalar()
        if active_provider == "gemini":
            active_connection_id = gemini_id

    if row[5]:
        openai_id = conn.execute(
            sa.text(
                "INSERT INTO ai_ocr_connections (provider, model, account, api_key) "
                "VALUES ('openai', :model, :account, :api_key) RETURNING id"
            ),
            {"model": row[6] or "gpt-4o", "account": row[4], "api_key": row[5]},
        ).scalar()
        if active_provider == "openai":
            active_connection_id = openai_id

    if active_connection_id is not None:
        conn.execute(
            sa.text("UPDATE ai_ocr_settings SET active_connection_id = :cid WHERE id = 1"),
            {"cid": active_connection_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_ai_ocr_settings_active_connection", "ai_ocr_settings", type_="foreignkey")
    op.drop_column("ai_ocr_settings", "active_connection_id")
    op.drop_index("ix_ai_ocr_connections_provider", table_name="ai_ocr_connections")
    op.drop_table("ai_ocr_connections")
