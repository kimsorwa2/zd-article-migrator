from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    DeleteExecuteRequest,
    DeleteExecuteResponse,
    DeleteFailedItemResponse,
    DeleteRetryRequest,
    DeleteSummaryResponse,
)
from db.database import get_async_session
from services.delete_service import DeleteExecuteResult, DeleteService

router = APIRouter(prefix="/delete", tags=["delete"])


def _to_execute_response(
    source_instance_id: int,
    target_instance_id: int,
    result: DeleteExecuteResult,
) -> DeleteExecuteResponse:
    return DeleteExecuteResponse(
        source_instance_id=source_instance_id,
        target_instance_id=target_instance_id,
        summary=DeleteSummaryResponse(
            categories=result.summary.categories,
            sections=result.summary.sections,
            articles=result.summary.articles,
        ),
        failed_items=[
            DeleteFailedItemResponse(
                mapping_id=item.mapping_id,
                entity_type=item.entity_type,
                target_a_id=item.target_a_id,
                error_message=item.error_message,
            )
            for item in result.failed_items
        ],
    )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    /**
     * 삭제 라우터의 연결 상태를 확인한다.
     * @returns {dict[str, str]} 라우터 상태 메시지
     */
    """
    return {"message": "delete router is ready"}


@router.post("/preview", response_model=DeleteExecuteResponse)
async def preview_delete(
    payload: DeleteExecuteRequest,
    session: AsyncSession = Depends(get_async_session),
) -> DeleteExecuteResponse:
    """
    /**
     * 삭제 실행 전 예상 삭제 건수를 계산해 반환한다.
     */
    """
    try:
        summary = await DeleteService.preview(
            session=session,
            source_instance_id=payload.source_instance_id,
            target_instance_id=payload.target_instance_id,
            brand_a_ids=payload.brand_a_ids,
            category_a_ids=payload.category_a_ids,
            section_a_ids=payload.section_a_ids,
            article_a_ids=payload.article_a_ids,
            target_category_a_ids=payload.target_category_a_ids,
            target_section_a_ids=payload.target_section_a_ids,
            target_article_a_ids=payload.target_article_a_ids,
            target_brand_id=payload.target_brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return DeleteExecuteResponse(
        source_instance_id=payload.source_instance_id,
        target_instance_id=payload.target_instance_id,
        summary=DeleteSummaryResponse(
            categories=summary.categories,
            sections=summary.sections,
            articles=summary.articles,
        ),
        failed_items=[],
    )


@router.post("/execute", response_model=DeleteExecuteResponse)
async def execute_delete(
    payload: DeleteExecuteRequest,
    session: AsyncSession = Depends(get_async_session),
) -> DeleteExecuteResponse:
    """
    /**
     * migrated 상태 항목을 타겟 Zendesk에서 삭제하고 매핑을 정리한다.
     */
    """
    try:
        result = await DeleteService.execute(
            session=session,
            source_instance_id=payload.source_instance_id,
            target_instance_id=payload.target_instance_id,
            brand_a_ids=payload.brand_a_ids,
            category_a_ids=payload.category_a_ids,
            section_a_ids=payload.section_a_ids,
            article_a_ids=payload.article_a_ids,
            target_category_a_ids=payload.target_category_a_ids,
            target_section_a_ids=payload.target_section_a_ids,
            target_article_a_ids=payload.target_article_a_ids,
            target_brand_id=payload.target_brand_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return _to_execute_response(payload.source_instance_id, payload.target_instance_id, result)


@router.post("/retry", response_model=DeleteExecuteResponse)
async def retry_delete(
    payload: DeleteRetryRequest,
    session: AsyncSession = Depends(get_async_session),
) -> DeleteExecuteResponse:
    """
    /**
     * delete_error 상태 매핑에 대해 삭제를 재시도한다.
     */
    """
    try:
        result = await DeleteService.retry_failed(
            session=session,
            source_instance_id=payload.source_instance_id,
            target_instance_id=payload.target_instance_id,
            target_brand_id=payload.target_brand_id,
            mapping_ids=payload.mapping_ids or None,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return _to_execute_response(payload.source_instance_id, payload.target_instance_id, result)
