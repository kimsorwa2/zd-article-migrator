from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

MigrateProgressStatus = Literal["idle", "running", "completed", "failed"]


def migrate_job_key(source_instance_id: int, target_instance_id: int) -> str:
    """
    /**
     * 소스·타겟 인스턴스 쌍으로 마이그레이션 작업 키를 만든다.
     * @param {int} source_instance_id 소스 인스턴스 ID
     * @param {int} target_instance_id 타겟 인스턴스 ID
     * @returns {str} 작업 식별 키
     */
    """
    return f"{source_instance_id}:{target_instance_id}"


@dataclass
class MigrateProgressSnapshot:
    """
    /**
     * 마이그레이션 진행 상태 스냅샷(프론트 폴링용).
     */
    """

    source_instance_id: int
    target_instance_id: int
    status: MigrateProgressStatus = "idle"
    percent: int = 0
    message: str = ""
    phase: str = ""
    current_step: int = 0
    total_steps: int = 0
    error: str | None = None
    result: dict[str, Any] | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_instance_id": self.source_instance_id,
            "target_instance_id": self.target_instance_id,
            "status": self.status,
            "percent": self.percent,
            "message": self.message,
            "phase": self.phase,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "error": self.error,
            "result": self.result,
            "updated_at": self.updated_at.isoformat(),
        }


class MigrateProgressTracker:
    """
    /**
     * 인스턴스 쌍별 마이그레이션 진행 상태를 메모리에 보관한다.
     */
    """

    _lock = asyncio.Lock()
    _states: dict[str, MigrateProgressSnapshot] = {}

    @classmethod
    async def get_snapshot(cls, source_instance_id: int, target_instance_id: int) -> MigrateProgressSnapshot:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            state = cls._states.get(key)
            if state is None:
                return MigrateProgressSnapshot(
                    source_instance_id=source_instance_id,
                    target_instance_id=target_instance_id,
                    status="idle",
                    message="마이그레이션 대기 중",
                )
            return state

    @classmethod
    def is_running(cls, source_instance_id: int, target_instance_id: int) -> bool:
        key = migrate_job_key(source_instance_id, target_instance_id)
        state = cls._states.get(key)
        return state is not None and state.status == "running"

    @classmethod
    async def start(cls, source_instance_id: int, target_instance_id: int, total_steps: int) -> None:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            cls._states[key] = MigrateProgressSnapshot(
                source_instance_id=source_instance_id,
                target_instance_id=target_instance_id,
                status="running",
                percent=0,
                message="마이그레이션을 시작합니다.",
                phase="preparing",
                total_steps=max(total_steps, 1),
            )
        await cls._log_progress(key)

    @classmethod
    async def update_step(
        cls,
        source_instance_id: int,
        target_instance_id: int,
        *,
        current_step: int,
        phase: str,
        message: str,
    ) -> None:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            state = cls._require_running(key)
            state.current_step = current_step
            state.phase = phase
            state.message = message
            total = max(state.total_steps, 1)
            state.percent = max(0, min(99, int((current_step / total) * 100)))
            state.updated_at = datetime.now(UTC)
        await cls._log_progress(key)

    @classmethod
    async def complete(cls, source_instance_id: int, target_instance_id: int, result: dict[str, Any]) -> None:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            state = cls._require_running(key)
            state.status = "completed"
            state.percent = 100
            state.phase = "done"
            state.message = "마이그레이션이 완료되었습니다."
            state.result = result
            state.updated_at = datetime.now(UTC)
        await cls._log_progress(key)

    @classmethod
    async def fail(cls, source_instance_id: int, target_instance_id: int, error_message: str) -> None:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            state = cls._states.get(key)
            if state is None:
                state = MigrateProgressSnapshot(
                    source_instance_id=source_instance_id,
                    target_instance_id=target_instance_id,
                )
                cls._states[key] = state
            state.status = "failed"
            state.error = error_message
            state.message = "마이그레이션에 실패했습니다."
            state.updated_at = datetime.now(UTC)
        logger.error(
            "[마이그레이션 실패] source=%s target=%s %s",
            source_instance_id,
            target_instance_id,
            error_message,
        )

    @classmethod
    async def reset_idle(cls, source_instance_id: int, target_instance_id: int) -> None:
        key = migrate_job_key(source_instance_id, target_instance_id)
        async with cls._lock:
            cls._states.pop(key, None)

    @classmethod
    def _require_running(cls, key: str) -> MigrateProgressSnapshot:
        state = cls._states.get(key)
        if state is None or state.status != "running":
            raise RuntimeError(f"진행 중인 마이그레이션 작업이 없습니다: {key}")
        return state

    @classmethod
    async def _log_progress(cls, key: str) -> None:
        async with cls._lock:
            state = cls._states.get(key)
            if state is None:
                return
            logger.info(
                "[마이그레이션 진행 %s%%] source=%s target=%s phase=%s step=%s/%s | %s",
                state.percent,
                state.source_instance_id,
                state.target_instance_id,
                state.phase,
                state.current_step,
                state.total_steps,
                state.message,
            )
