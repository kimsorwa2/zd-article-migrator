from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

FetchProgressStatus = Literal["idle", "running", "completed", "failed"]

# 브랜드 1개 안에서 단계별 진행 가중치(합 1.0)
_BRAND_STEP_WEIGHTS: dict[str, float] = {
    "brand_meta": 0.05,
    "categories": 0.1,
    "sections": 0.1,
    "articles": 0.55,
    "attachments": 0.15,
    "saving": 0.05,
}


@dataclass
class FetchProgressSnapshot:
    """
    /**
     * 수집 진행 상태 스냅샷(프론트 폴링·터미널 로그용).
     */
    """

    instance_id: int
    status: FetchProgressStatus = "idle"
    percent: int = 0
    message: str = ""
    phase: str = ""
    brand_index: int = 0
    brand_total: int = 0
    brand_name: str | None = None
    article_page: int = 0
    articles_collected: int = 0
    attachments_checked: int = 0
    attachments_total: int = 0
    error: str | None = None
    result: dict[str, Any] | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "status": self.status,
            "percent": self.percent,
            "message": self.message,
            "phase": self.phase,
            "brand_index": self.brand_index,
            "brand_total": self.brand_total,
            "brand_name": self.brand_name,
            "article_page": self.article_page,
            "articles_collected": self.articles_collected,
            "attachments_checked": self.attachments_checked,
            "attachments_total": self.attachments_total,
            "error": self.error,
            "result": self.result,
            "updated_at": self.updated_at.isoformat(),
        }


class FetchProgressTracker:
    """
    /**
     * 인스턴스별 Help Center 수집 진행 상태를 메모리에 보관한다.
     */
    """

    _lock = asyncio.Lock()
    _states: dict[int, FetchProgressSnapshot] = {}

    @classmethod
    async def get_snapshot(cls, instance_id: int) -> FetchProgressSnapshot:
        async with cls._lock:
            state = cls._states.get(instance_id)
            if state is None:
                return FetchProgressSnapshot(instance_id=instance_id, status="idle", message="수집 대기 중")
            return state

    @classmethod
    def is_running(cls, instance_id: int) -> bool:
        state = cls._states.get(instance_id)
        return state is not None and state.status == "running"

    @classmethod
    async def start(cls, instance_id: int) -> None:
        async with cls._lock:
            cls._states[instance_id] = FetchProgressSnapshot(
                instance_id=instance_id,
                status="running",
                percent=0,
                message="Help Center 수집을 시작합니다.",
                phase="preparing",
            )
        await cls._log_progress(instance_id)

    @classmethod
    async def set_brand_total(cls, instance_id: int, brand_total: int) -> None:
        async with cls._lock:
            state = cls._require_running(instance_id)
            state.brand_total = brand_total
            state.message = f"브랜드 {brand_total}개 수집 예정"
            state.updated_at = datetime.now(UTC)
        await cls._log_progress(instance_id)

    @classmethod
    async def update_brand_step(
        cls,
        instance_id: int,
        *,
        brand_index: int,
        brand_name: str,
        phase: str,
        message: str,
        article_page: int = 0,
        articles_collected: int = 0,
        attachments_checked: int = 0,
        attachments_total: int = 0,
        article_page_cap: int | None = None,
    ) -> None:
        async with cls._lock:
            state = cls._require_running(instance_id)
            state.brand_index = brand_index
            state.brand_name = brand_name
            state.phase = phase
            state.message = message
            state.article_page = article_page
            state.articles_collected = articles_collected
            state.attachments_checked = attachments_checked
            state.attachments_total = attachments_total
            state.percent = cls._calc_percent(
                brand_index=brand_index,
                brand_total=state.brand_total,
                phase=phase,
                article_page=article_page,
                articles_collected=articles_collected,
                attachments_checked=attachments_checked,
                attachments_total=attachments_total,
                article_page_cap=article_page_cap,
            )
            state.updated_at = datetime.now(UTC)
        await cls._log_progress(instance_id)

    @classmethod
    async def complete(cls, instance_id: int, result: dict[str, Any]) -> None:
        async with cls._lock:
            state = cls._require_running(instance_id)
            state.status = "completed"
            state.percent = 100
            state.phase = "done"
            state.message = "Help Center 수집이 완료되었습니다."
            state.result = result
            state.updated_at = datetime.now(UTC)
        await cls._log_progress(instance_id)

    @classmethod
    async def fail(cls, instance_id: int, error_message: str) -> None:
        async with cls._lock:
            state = cls._states.get(instance_id)
            if state is None:
                state = FetchProgressSnapshot(instance_id=instance_id)
                cls._states[instance_id] = state
            state.status = "failed"
            state.error = error_message
            state.message = "Help Center 수집에 실패했습니다."
            state.updated_at = datetime.now(UTC)
        logger.error("[수집 실패] instance_id=%s %s", instance_id, error_message)

    @classmethod
    async def reset_idle(cls, instance_id: int) -> None:
        async with cls._lock:
            cls._states.pop(instance_id, None)

    @classmethod
    def _require_running(cls, instance_id: int) -> FetchProgressSnapshot:
        state = cls._states.get(instance_id)
        if state is None or state.status != "running":
            raise RuntimeError(f"진행 중인 수집 작업이 없습니다: instance_id={instance_id}")
        return state

    @classmethod
    def _calc_percent(
        cls,
        *,
        brand_index: int,
        brand_total: int,
        phase: str,
        article_page: int,
        articles_collected: int,
        attachments_checked: int,
        attachments_total: int,
        article_page_cap: int | None,
    ) -> int:
        if brand_total <= 0:
            if phase == "preparing":
                return 1
            return min(99, 2 + article_page)

        phase_order = list(_BRAND_STEP_WEIGHTS.keys())
        completed_in_brand = 0.0

        if phase in phase_order:
            phase_idx = phase_order.index(phase)
            completed_in_brand = sum(_BRAND_STEP_WEIGHTS[step] for step in phase_order[:phase_idx])
            current_weight = _BRAND_STEP_WEIGHTS[phase]
            if phase == "articles" and article_page > 0:
                cap = article_page_cap if article_page_cap and article_page_cap > 0 else 80
                completed_in_brand += current_weight * min(0.95, article_page / cap)
            elif phase == "attachments" and attachments_total > 0:
                completed_in_brand += current_weight * (attachments_checked / attachments_total)
            else:
                completed_in_brand += current_weight
        elif phase == "preparing":
            completed_in_brand = 0.0
        else:
            completed_in_brand = 0.02

        overall = ((max(brand_index, 1) - 1) + completed_in_brand) / brand_total
        return max(0, min(99, int(overall * 100)))

    @classmethod
    async def _log_progress(cls, instance_id: int) -> None:
        async with cls._lock:
            state = cls._states.get(instance_id)
            if state is None:
                return
            logger.info(
                "[수집 진행 %s%%] instance_id=%s phase=%s brand=%s/%s (%s) articles=%s page=%s attachments=%s/%s | %s",
                state.percent,
                instance_id,
                state.phase,
                state.brand_index,
                state.brand_total,
                state.brand_name or "-",
                state.articles_collected,
                state.article_page,
                state.attachments_checked,
                state.attachments_total,
                state.message,
            )
