from __future__ import annotations



import logging



from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession



from api.schemas import (

    FetchBrandSummaryResponse,

    FetchDetailResponse,

    FetchSyncProgressResponse,

    FetchSyncResponse,

    FetchSyncStartResponse,

    SyncCountsResponse,

)

from db.database import get_async_session

from services.fetch_progress import FetchProgressTracker

from services.fetch_service import FetchService

from services.fetch_sync_job import start_sync_job

from services.zendesk_client import ZendeskClientError



router = APIRouter(prefix="/fetch", tags=["fetch"])

logger = logging.getLogger(__name__)





def _to_sync_counts_response(counts) -> SyncCountsResponse:

    """

    /**

     * SyncCounts dataclass를 API 응답 스키마로 변환한다.

     * @param counts 동기화 건수 dataclass

     * @returns {SyncCountsResponse} API 응답 객체

     */

    """

    return SyncCountsResponse(created=counts.created, updated=counts.updated, deleted=counts.deleted)





def _progress_to_response(snapshot) -> FetchSyncProgressResponse:

    result = None

    if snapshot.result is not None:

        result = FetchSyncResponse.model_validate(snapshot.result)

    return FetchSyncProgressResponse(

        instance_id=snapshot.instance_id,

        status=snapshot.status,

        percent=snapshot.percent,

        message=snapshot.message,

        phase=snapshot.phase,

        brand_index=snapshot.brand_index,

        brand_total=snapshot.brand_total,

        brand_name=snapshot.brand_name,

        article_page=snapshot.article_page,

        articles_collected=snapshot.articles_collected,

        attachments_checked=snapshot.attachments_checked,

        attachments_total=snapshot.attachments_total,

        error=snapshot.error,

        result=result,

    )





@router.get("/health")

async def health_check() -> dict[str, str]:

    """

    /**

     * 데이터 수집 라우터의 연결 상태를 확인한다.

     * @returns {dict[str, str]} 라우터 상태 메시지

     */

    """

    return {"message": "fetch router is ready"}





@router.get("/{instance_id}/sync/progress", response_model=FetchSyncProgressResponse)

async def get_sync_progress(instance_id: int) -> FetchSyncProgressResponse:

    """

    /**

     * Help Center 수집 진행률을 조회한다(프론트 폴링용).

     * @param {int} instance_id 인스턴스 ID

     * @returns {FetchSyncProgressResponse} 진행 상태

     */

    """

    snapshot = await FetchProgressTracker.get_snapshot(instance_id)

    return _progress_to_response(snapshot)





@router.get("/{instance_id}/detail", response_model=FetchDetailResponse)

async def get_source_instance_fetch_detail(

    instance_id: int,

    session: AsyncSession = Depends(get_async_session),

) -> FetchDetailResponse:

    """

    /**

     * source 인스턴스에 저장된 수집 데이터 상세를 조회한다.

     * @param {int} instance_id 조회할 source 인스턴스 ID

     * @param {AsyncSession} session 비동기 DB 세션

     * @returns {FetchDetailResponse} 브랜드 트리 및 요약 정보

     */

    """

    try:

        detail = await FetchService.get_fetch_detail(session=session, instance_id=instance_id)

    except ValueError as error:

        logger.warning("수집 상세 조회 실패: instance_id=%s, reason=%s", instance_id, error)

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error



    return FetchDetailResponse.model_validate(detail)





@router.post("/{instance_id}/sync", response_model=FetchSyncStartResponse, status_code=status.HTTP_202_ACCEPTED)

async def sync_source_instance_data(instance_id: int) -> FetchSyncStartResponse:

    """

    /**

     * Help Center 수집을 백그라운드로 시작한다. 진행률은 GET /sync/progress로 조회한다.

     * @param {int} instance_id 수집할 인스턴스 ID

     * @returns {FetchSyncStartResponse} 작업 시작 응답

     */

    """

    if FetchProgressTracker.is_running(instance_id):

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail="이미 Help Center 수집이 진행 중입니다.",

        )



    try:

        start_sync_job(instance_id)

    except RuntimeError as error:

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error



    logger.info("수집 작업 요청 수락: instance_id=%s", instance_id)

    return FetchSyncStartResponse(instance_id=instance_id, status="running")


