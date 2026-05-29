from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    MigrateExecuteRequest,
    MigrateExecuteResponse,
    MigrateExecuteStartResponse,
    MigrateOverlayResponse,
    MigrateProgressResponse,
    MigrateSummaryResponse,
    MigrateTreeResponse,
)
from db.database import get_async_session
from services.migrate_progress import MigrateProgressTracker
from services.migrate_sync_job import start_migrate_job
from services.migration_service import MigrationService
from services.zendesk_client import ZendeskClientError

router = APIRouter(prefix="/migrate", tags=["migrate"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    /**
     * 마이그레이션 라우터의 연결 상태를 확인한다.
     * @returns {dict[str, str]} 라우터 상태 메시지
     */
    """
    return {"message": "migrate router is ready"}


def _progress_to_response(snapshot) -> MigrateProgressResponse:
    result = None
    if snapshot.result is not None:
        summary_data = snapshot.result.get("summary", {})
        result = MigrateExecuteResponse(
            source_instance_id=snapshot.source_instance_id,
            target_instance_id=snapshot.target_instance_id,
            summary=MigrateSummaryResponse(
                brands=summary_data.get("brands", 0),
                categories=summary_data.get("categories", 0),
                sections=summary_data.get("sections", 0),
                articles=summary_data.get("articles", 0),
            ),
        )
    return MigrateProgressResponse(
        source_instance_id=snapshot.source_instance_id,
        target_instance_id=snapshot.target_instance_id,
        status=snapshot.status,
        percent=snapshot.percent,
        message=snapshot.message,
        phase=snapshot.phase,
        current_step=snapshot.current_step,
        total_steps=snapshot.total_steps,
        error=snapshot.error,
        result=result,
    )


@router.get("/progress", response_model=MigrateProgressResponse)
async def get_migration_progress(
    source_instance_id: int = Query(..., ge=1),
    target_instance_id: int = Query(..., ge=1),
) -> MigrateProgressResponse:
    """
    /**
     * 마이그레이션 진행률을 조회한다(프론트 폴링용).
     */
    """
    snapshot = await MigrateProgressTracker.get_snapshot(source_instance_id, target_instance_id)
    return _progress_to_response(snapshot)


@router.post(
    "/execute",
    response_model=MigrateExecuteStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_migration(
    payload: MigrateExecuteRequest,
) -> MigrateExecuteStartResponse:
    """
    /**
     * 선택한 엔티티 마이그레이션을 백그라운드에서 시작한다.
     */
    """
    if payload.source_instance_id == payload.target_instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="소스와 타겟 인스턴스는 서로 달라야 합니다.",
        )

    if MigrateProgressTracker.is_running(payload.source_instance_id, payload.target_instance_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 마이그레이션이 진행 중입니다.",
        )

    total_steps = max(
        1,
        len(payload.brand_ids)
        + len(payload.category_ids)
        + len(payload.section_ids)
        + len(payload.article_ids),
    )

    try:
        start_migrate_job(
            source_instance_id=payload.source_instance_id,
            target_instance_id=payload.target_instance_id,
            duplicate_policy=payload.duplicate_policy,
            brand_ids=payload.brand_ids,
            category_ids=payload.category_ids,
            section_ids=payload.section_ids,
            article_ids=payload.article_ids,
            target_brand_id=payload.target_brand_id,
            total_steps=total_steps,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return MigrateExecuteStartResponse(
        source_instance_id=payload.source_instance_id,
        target_instance_id=payload.target_instance_id,
        status="running",
    )


@router.get("/overlay", response_model=MigrateOverlayResponse)
async def get_migration_overlay(
    source_instance_id: int = Query(..., ge=1),
    target_instance_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_async_session),
) -> MigrateOverlayResponse:
    """
    /**
     * 타겟 Help Center 트리에 표시할 migrated 오버레이 정보를 조회한다.
     */
    """
    try:
        data = await MigrationService.get_target_overlay(
            session=session,
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return MigrateOverlayResponse.model_validate(data)


@router.get("/tree", response_model=MigrateTreeResponse)
async def get_migration_tree(
    source_instance_id: int = Query(..., ge=1),
    target_instance_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_async_session),
) -> MigrateTreeResponse:
    """
    /**
     * 선택 가능한 마이그레이션 트리 데이터를 매핑 상태와 함께 조회한다.
     */
    """
    try:
        tree = await MigrationService.get_selection_tree(
            session=session,
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return MigrateTreeResponse(
        source_instance_id=source_instance_id,
        target_instance_id=target_instance_id,
        brands=tree,
    )
