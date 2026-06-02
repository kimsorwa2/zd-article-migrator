from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 선언형 베이스 클래스."""


# 애플리케이션 시작 시 backend/.env 값을 우선 로드한다.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/zd_article_migrator",
)

# Neon PostgreSQL: 연결 유효성 검사 + 주기적 풀 교체.
# asyncpg/SQLAlchemy prepared statement 캐시를 모두 끄면,
# alembic 마이그레이션 직후 InvalidCachedStatementError를 피할 수 있다.
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)


async def dispose_engine_pool() -> None:
    """
    /**
     * 연결 풀을 비운다. 스키마 변경 후 stale prepared statement 제거용.
     */
    """
    await engine.dispose()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    /**
     * 데이터베이스 비동기 세션을 FastAPI 의존성으로 제공한다.
     * @returns {AsyncGenerator[AsyncSession, None]} 요청 단위 비동기 세션 제너레이터
     */
    """
    async with AsyncSessionLocal() as session:
        yield session
