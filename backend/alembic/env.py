from __future__ import annotations

import os
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from db.connection import prepare_asyncpg_database
from db.models import Base

# Alembic 실행 시에도 backend/.env 값을 명시적으로 로드한다.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_raw_database_url = os.getenv("DATABASE_URL")
_database_url = _raw_database_url
_connect_args: dict[str, object] = {
    "prepared_statement_cache_size": 0,
    "statement_cache_size": 0,
}
if _raw_database_url:
    _database_url, _connect_args = prepare_asyncpg_database(_raw_database_url)
    config.set_main_option("sqlalchemy.url", _database_url)


def run_migrations_offline() -> None:
    """
    /**
     * 오프라인 모드에서 마이그레이션 SQL을 생성한다.
     * @returns {None} 반환값 없음
     */
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    /**
     * 연결된 DB 세션에서 마이그레이션을 실행한다.
     * @param {Connection} connection Alembic이 사용할 동기 연결 객체
     * @returns {None} 반환값 없음
     */
    """
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    /**
     * 온라인 모드에서 비동기 엔진을 통해 마이그레이션을 실행한다.
     * @returns {None} 반환값 없음
     */
    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
