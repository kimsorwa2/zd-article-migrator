import logging

from fastapi import FastAPI

from api.routers import delete, fetch, instances, migrate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
for logger_name in ("services", "services.fetch_service", "services.fetch_progress", "services.fetch_sync_job"):
    logging.getLogger(logger_name).setLevel(logging.INFO)

app = FastAPI(
    title="zd-article-migrator",
    description="Zendesk 아티클 마이그레이션 백엔드 API",
    version="0.1.0",
)

app.include_router(instances.router, prefix="/api")
app.include_router(fetch.router, prefix="/api")
app.include_router(migrate.router, prefix="/api")
app.include_router(delete.router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """
    /**
     * 애플리케이션 기본 상태를 반환한다.
     * @returns {dict[str, str]} 서버 상태 정보
     */
    """
    return {"status": "ok"}
