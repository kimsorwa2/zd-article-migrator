from __future__ import annotations

import asyncio
import logging

from db.database import AsyncSessionLocal
from services.fetch_progress import FetchProgressTracker
from services.fetch_service import FetchBrandSummary, FetchService
from services.zendesk_client import ZendeskClientError

logger = logging.getLogger(__name__)

_running_tasks: dict[int, asyncio.Task[None]] = {}


def _summaries_to_result(instance_id: int, summaries: list[FetchBrandSummary]) -> dict:
    return {
        "instance_id": instance_id,
        "processed_brands": len(summaries),
        "brand_summaries": [
            {
                "brand_id": item.brand_id,
                "brand_name": item.brand_name,
                "categories": {
                    "created": item.categories.created,
                    "updated": item.categories.updated,
                    "deleted": item.categories.deleted,
                },
                "sections": {
                    "created": item.sections.created,
                    "updated": item.sections.updated,
                    "deleted": item.sections.deleted,
                },
                "articles": {
                    "created": item.articles.created,
                    "updated": item.articles.updated,
                    "deleted": item.articles.deleted,
                },
            }
            for item in summaries
        ],
    }


async def _run_sync_job(instance_id: int) -> None:
    logger.info("[수집 작업 시작] instance_id=%s", instance_id)
    try:
        async with AsyncSessionLocal() as session:
            summaries = await FetchService.sync_source_instance(session=session, instance_id=instance_id)
        result = _summaries_to_result(instance_id, summaries)
        await FetchProgressTracker.complete(instance_id, result)
        logger.info("[수집 작업 완료] instance_id=%s, brands=%s", instance_id, len(summaries))
    except (ValueError, ZendeskClientError) as error:
        await FetchProgressTracker.fail(instance_id, str(error))
        logger.exception("[수집 작업 실패] instance_id=%s", instance_id)
    except Exception as error:
        await FetchProgressTracker.fail(instance_id, f"예기치 않은 오류: {error}")
        logger.exception("[수집 작업 실패] instance_id=%s", instance_id)
    finally:
        _running_tasks.pop(instance_id, None)


def start_sync_job(instance_id: int) -> None:
    if FetchProgressTracker.is_running(instance_id):
        raise RuntimeError("이미 수집이 진행 중입니다.")
    task = asyncio.create_task(_run_sync_job(instance_id))
    _running_tasks[instance_id] = task
