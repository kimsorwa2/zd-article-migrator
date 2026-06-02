from __future__ import annotations

import asyncio
import logging

from db.database import AsyncSessionLocal
from services.migrate_progress import MigrateProgressTracker
from services.migration_service import MigrationService
from services.zendesk_client import ZendeskClientError

logger = logging.getLogger(__name__)

_running_tasks: dict[str, asyncio.Task[None]] = {}


def _summary_to_result(source_instance_id: int, target_instance_id: int, summary) -> dict:
    return {
        "source_instance_id": source_instance_id,
        "target_instance_id": target_instance_id,
        "summary": {
            "brands": summary.brands,
            "categories": summary.categories,
            "sections": summary.sections,
            "articles": summary.articles,
            "scope_categories": summary.scope_categories,
            "scope_sections": summary.scope_sections,
            "scope_articles": summary.scope_articles,
        },
    }


async def _run_migrate_job(
    *,
    source_instance_id: int,
    target_instance_id: int,
    duplicate_policy: str,
    brand_ids: list[int],
    category_ids: list[int],
    section_ids: list[int],
    article_ids: list[int],
    target_brand_id: int | None,
) -> None:
    job_key = f"{source_instance_id}:{target_instance_id}"
    logger.info("[마이그레이션 작업 시작] %s", job_key)
    try:
        async with AsyncSessionLocal() as session:
            summary = await MigrationService.execute(
                session=session,
                source_instance_id=source_instance_id,
                target_instance_id=target_instance_id,
                duplicate_policy=duplicate_policy,
                brand_ids=brand_ids,
                category_ids=category_ids,
                section_ids=section_ids,
                article_ids=article_ids,
                target_brand_id=target_brand_id,
                report_progress=True,
            )
        result = _summary_to_result(source_instance_id, target_instance_id, summary)
        await MigrateProgressTracker.complete(source_instance_id, target_instance_id, result)
        logger.info("[마이그레이션 작업 완료] %s", job_key)
    except (ValueError, ZendeskClientError) as error:
        await MigrateProgressTracker.fail(source_instance_id, target_instance_id, str(error))
        logger.exception("[마이그레이션 작업 실패] %s", job_key)
    except Exception as error:
        await MigrateProgressTracker.fail(source_instance_id, target_instance_id, f"예기치 않은 오류: {error}")
        logger.exception("[마이그레이션 작업 실패] %s", job_key)
    finally:
        _running_tasks.pop(job_key, None)


def start_migrate_job(
    *,
    source_instance_id: int,
    target_instance_id: int,
    duplicate_policy: str,
    brand_ids: list[int],
    category_ids: list[int],
    section_ids: list[int],
    article_ids: list[int],
    target_brand_id: int | None,
    total_steps: int,
) -> None:
    """
    /**
     * 마이그레이션 백그라운드 작업을 시작한다.
     */
    """
    if MigrateProgressTracker.is_running(source_instance_id, target_instance_id):
        raise RuntimeError("이미 마이그레이션이 진행 중입니다.")

    job_key = f"{source_instance_id}:{target_instance_id}"

    async def _wrapped() -> None:
        await MigrateProgressTracker.start(source_instance_id, target_instance_id, total_steps)
        await _run_migrate_job(
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            duplicate_policy=duplicate_policy,
            brand_ids=brand_ids,
            category_ids=category_ids,
            section_ids=section_ids,
            article_ids=article_ids,
            target_brand_id=target_brand_id,
        )

    task = asyncio.create_task(_wrapped())
    _running_tasks[job_key] = task
