from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ConnectionTestResponse,
    CreateInstanceRequest,
    CreateSourceInstanceRequest,
    CreateTargetInstanceRequest,
    InstanceDetailResponse,
    InstanceResponse,
    SourceBrandPreviewRequest,
    SourceBrandResponse,
    SourceInstanceResponse,
    UpdateInstanceRequest,
    UpdateInstanceActiveRequest,
)

INSTANCE_ROLE = "zendesk"
from db.database import get_async_session
from db.models import Brand, Instance
from services.fetch_progress import FetchProgressTracker
from services.zendesk_client import ZendeskClient, ZendeskClientError

router = APIRouter(prefix="/instances", tags=["instances"])


def normalize_subdomain(raw_subdomain: str) -> str:
    """
    /**
     * 입력된 서브도메인 문자열을 API 처리용 표준 형태로 정규화한다.
     * @param {str} raw_subdomain 사용자가 입력한 서브도메인 문자열
     * @returns {str} ".zendesk.com" 접미사가 제거된 서브도메인
     */
    """
    return raw_subdomain.strip().replace(".zendesk.com", "")


def resolve_instance_name(name: str | None, subdomain: str) -> str:
    """
    /**
     * 인스턴스 저장 시 사용할 최종 이름을 결정한다.
     * @param {str | None} name 사용자가 입력한 인스턴스 이름
     * @param {str} subdomain 정규화된 Zendesk 서브도메인
     * @returns {str} 이름 입력값 또는 서브도메인 기반 기본 이름
     */
    """
    if name is not None and name.strip():
        return name.strip()

    if "." in subdomain:
        return subdomain.split(".", maxsplit=1)[0].strip()

    return subdomain.strip()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    /**
     * 인스턴스 라우터의 연결 상태를 확인한다.
     * @returns {dict[str, str]} 라우터 상태 메시지
     */
    """
    return {"message": "instances router is ready"}


@router.post("/brands/preview", response_model=list[SourceBrandResponse])
async def preview_instance_brands(payload: SourceBrandPreviewRequest) -> list[SourceBrandResponse]:
    """
    /**
     * 인증값으로 Zendesk 브랜드 목록을 미리 조회한다.
     * @param {SourceBrandPreviewRequest} payload Zendesk 인증 요청 데이터
     * @returns {list[SourceBrandResponse]} 선택 가능한 브랜드 목록
     */
    """
    return await preview_source_brands(payload)


@router.post("/source/brands/preview", response_model=list[SourceBrandResponse])
async def preview_source_brands(payload: SourceBrandPreviewRequest) -> list[SourceBrandResponse]:
    """
    /**
     * 소스 인스턴스 인증값으로 브랜드 목록을 미리 조회한다.
     * @param {SourceBrandPreviewRequest} payload 소스 Zendesk 인증 요청 데이터
     * @returns {list[SourceBrandResponse]} 선택 가능한 브랜드 목록
     */
    """
    try:
        brands = await ZendeskClient.get_brands(
            main_subdomain=payload.subdomain,
            email=payload.email,
            api_token=payload.api_token,
        )
    except ZendeskClientError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return [
        SourceBrandResponse(
            id=0,
            a_brand_id=brand.id,
            name=brand.name,
            subdomain=brand.subdomain,
            has_help_center=brand.has_help_center,
        )
        for brand in brands
    ]


async def _create_instance_with_brands(
    session: AsyncSession,
    payload: CreateInstanceRequest,
) -> InstanceDetailResponse:
    """
    /**
     * Zendesk 인스턴스를 생성하고 브랜드 목록을 함께 저장한다.
     * @param {AsyncSession} session 비동기 DB 세션
     * @param {CreateInstanceRequest} payload 인스턴스 생성 요청 데이터
     * @returns {InstanceDetailResponse} 생성된 인스턴스 상세 정보
     */
    """
    normalized_subdomain = normalize_subdomain(payload.subdomain)

    duplicate_query = select(Instance).where(
        Instance.subdomain == normalized_subdomain,
        Instance.email == payload.email,
    )
    duplicate = await session.scalar(duplicate_query)
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 인스턴스입니다.",
        )

    try:
        brands = await ZendeskClient.get_brands(
            main_subdomain=normalized_subdomain,
            email=payload.email,
            api_token=payload.api_token,
        )
    except ZendeskClientError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    selected_brand_ids = set(payload.selected_brand_ids)
    instance = Instance(
        name=resolve_instance_name(payload.name, normalized_subdomain),
        subdomain=normalized_subdomain,
        email=payload.email,
        api_token=payload.api_token,
        role=INSTANCE_ROLE,
        is_active=True,
    )
    session.add(instance)
    await session.flush()

    brand_rows: list[Brand] = []
    for brand in brands:
        is_selected = brand.id in selected_brand_ids if selected_brand_ids else True
        brand_row = Brand(
            instance_id=instance.id,
            a_brand_id=brand.id,
            name=brand.name,
            subdomain=brand.subdomain,
            has_help_center=brand.has_help_center,
            is_selected=is_selected,
        )
        brand_rows.append(brand_row)
        session.add(brand_row)

    await session.commit()
    await session.refresh(instance)

    return InstanceDetailResponse(
        **InstanceResponse.model_validate(instance).model_dump(),
        brands=[
            SourceBrandResponse(
                id=row.id,
                a_brand_id=row.a_brand_id,
                name=row.name,
                subdomain=row.subdomain,
                has_help_center=row.has_help_center,
            )
            for row in brand_rows
        ],
    )


@router.post("", response_model=InstanceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: CreateInstanceRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceDetailResponse:
    """
    /**
     * Zendesk 인스턴스를 생성하고 브랜드 목록을 함께 저장한다.
     * @param {CreateInstanceRequest} payload 인스턴스/인증 정보 및 선택 브랜드 ID
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {InstanceDetailResponse} 생성된 인스턴스 상세 정보
     */
    """
    return await _create_instance_with_brands(session=session, payload=payload)


@router.post("/source", response_model=SourceInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_source_instance(
    payload: CreateSourceInstanceRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SourceInstanceResponse:
    """
    /**
     * 소스 인스턴스를 생성하고 Zendesk 브랜드 목록을 함께 저장한다.
     * @param {CreateSourceInstanceRequest} payload 인스턴스/인증 정보 및 선택 브랜드 ID
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {SourceInstanceResponse} 생성된 소스 인스턴스 상세 정보
     */
    """
    detail = await _create_instance_with_brands(session=session, payload=payload)
    return SourceInstanceResponse.model_validate(detail.model_dump())


@router.post("/target", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_target_instance(
    payload: CreateTargetInstanceRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceResponse:
    """
    /**
     * 타겟 인스턴스를 생성하기 전에 Zendesk 계정 연결을 검증한다.
     * @param {CreateTargetInstanceRequest} payload 타겟 인스턴스 생성 요청 데이터
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {InstanceResponse} 생성된 타겟 인스턴스 정보
     */
    """
    normalized_subdomain = normalize_subdomain(payload.subdomain)

    create_payload = CreateInstanceRequest(
        name=payload.name,
        subdomain=payload.subdomain,
        email=payload.email,
        api_token=payload.api_token,
        selected_brand_ids=[],
    )
    detail = await _create_instance_with_brands(session=session, payload=create_payload)
    return InstanceResponse.model_validate(detail.model_dump())


@router.get("", response_model=list[InstanceResponse])
async def list_instances(session: AsyncSession = Depends(get_async_session)) -> list[InstanceResponse]:
    """
    /**
     * 등록된 인스턴스 목록을 조회한다.
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {list[InstanceResponse]} 인스턴스 목록
     */
    """
    query = select(Instance).order_by(Instance.created_at.desc())
    result = await session.execute(query)
    instances = result.scalars().all()
    return [InstanceResponse.model_validate(instance) for instance in instances]


@router.get("/{instance_id}", response_model=InstanceDetailResponse)
async def get_instance(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceDetailResponse:
    """
    /**
     * 인스턴스 단건 상세를 조회한다.
     * @param {int} instance_id 조회할 인스턴스 ID
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {InstanceDetailResponse} 인스턴스 상세 정보
     */
    """
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    brands_query = select(Brand).where(Brand.instance_id == instance.id).order_by(Brand.name.asc())
    brands_result = await session.execute(brands_query)
    brands = brands_result.scalars().all()

    return InstanceDetailResponse(
        **InstanceResponse.model_validate(instance).model_dump(),
        brands=[
            SourceBrandResponse(
                id=brand.id,
                a_brand_id=brand.a_brand_id,
                name=brand.name,
                subdomain=brand.subdomain,
                has_help_center=brand.has_help_center,
            )
            for brand in brands
        ],
    )


@router.patch("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: int,
    payload: UpdateInstanceRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceResponse:
    """
    /**
     * 인스턴스의 이름/이메일/API 토큰을 수정하고 연결 유효성을 검증한다.
     * @param {int} instance_id 수정할 인스턴스 ID
     * @param {UpdateInstanceRequest} payload 수정 요청 데이터
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {InstanceResponse} 수정 후 인스턴스 정보
     */
    """
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    duplicate_query = select(Instance).where(
        Instance.subdomain == instance.subdomain,
        Instance.email == payload.email,
        Instance.id != instance_id,
    )
    duplicate = await session.scalar(duplicate_query)
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일한 이메일의 인스턴스가 이미 등록되어 있습니다.",
        )

    next_api_token = instance.api_token
    if payload.api_token is not None and payload.api_token.strip():
        next_api_token = payload.api_token.strip()

    try:
        await ZendeskClient.get_brands(
            main_subdomain=instance.subdomain,
            email=payload.email,
            api_token=next_api_token,
        )
    except ZendeskClientError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    instance.name = resolve_instance_name(payload.name, instance.subdomain)
    instance.email = payload.email
    instance.api_token = next_api_token
    await session.commit()
    await session.refresh(instance)

    return InstanceResponse.model_validate(instance)


@router.patch("/{instance_id}/active", response_model=InstanceResponse)
async def update_instance_active(
    instance_id: int,
    payload: UpdateInstanceActiveRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceResponse:
    """
    /**
     * 인스턴스 활성 상태를 변경한다.
     * @param {int} instance_id 변경 대상 인스턴스 ID
     * @param {UpdateInstanceActiveRequest} payload 활성 상태 변경 값
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {InstanceResponse} 변경 후 인스턴스 정보
     */
    """
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    instance.is_active = payload.is_active
    await session.commit()
    await session.refresh(instance)

    return InstanceResponse.model_validate(instance)


@router.post("/{instance_id}/connection-test", response_model=ConnectionTestResponse)
async def test_instance_connection(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> ConnectionTestResponse:
    """
    /**
     * 저장된 인스턴스 인증값으로 Zendesk 연결 테스트를 수행한다.
     * @param {int} instance_id 연결을 점검할 인스턴스 ID
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {ConnectionTestResponse} 연결 테스트 결과
     */
    """
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    try:
        await ZendeskClient.get_brands(
            main_subdomain=instance.subdomain,
            email=instance.email,
            api_token=instance.api_token,
        )
    except ZendeskClientError as error:
        return ConnectionTestResponse(success=False, message=str(error))

    return ConnectionTestResponse(success=True, message="연결 테스트에 성공했습니다.")


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """
    /**
     * 인스턴스와 연관된 수집·매핑 데이터를 DB에서 함께 삭제한다(CASCADE).
     * @param {int} instance_id 삭제할 인스턴스 ID
     * @param {AsyncSession} session 비동기 DB 세션
     * @returns {None} 성공 시 본문 없음(204)
     */
    """
    if FetchProgressTracker.is_running(instance_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Help Center 수집이 진행 중입니다. 수집이 끝난 뒤 삭제하세요.",
        )

    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    await session.delete(instance)
    await session.commit()
    await FetchProgressTracker.reset_idle(instance_id)
