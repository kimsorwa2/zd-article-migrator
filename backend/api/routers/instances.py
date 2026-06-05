from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ConnectionTestResponse,
    InstanceDetailResponse,
    InstanceResponse,
    OAuthConnectRequest,
    SourceBrandPreviewRequest,
    SourceBrandResponse,
    UpdateInstanceActiveRequest,
    UpdateInstanceRequest,
)
from db.database import get_async_session
from db.models import Brand, Instance
from services.fetch_progress import FetchProgressTracker
from services.zendesk_oauth_credentials import (
    ZendeskOAuthClientConfig,
    ZendeskOAuthError,
    apply_client_config_to_instance,
    build_client_config,
    config_from_instance,
)
from services.zendesk_oauth_service import ZendeskOAuthService, ZendeskOAuthTokens
from services.zendesk_client import ZendeskClientError

INSTANCE_ROLE = "zendesk"

router = APIRouter(prefix="/instances", tags=["instances"])


def normalize_subdomain(raw_subdomain: str) -> str:
    """입력 서브도메인에서 .zendesk.com 접미사를 제거한다."""
    return raw_subdomain.strip().replace(".zendesk.com", "")


def resolve_instance_name(name: str | None, subdomain: str) -> str:
    """인스턴스 저장용 표시 이름을 결정한다."""
    if name is not None and name.strip():
        return name.strip()
    if "." in subdomain:
        return subdomain.split(".", maxsplit=1)[0].strip()
    return subdomain.strip()


def to_instance_response(instance: Instance) -> InstanceResponse:
    """DB Instance → API 응답(OAuth 연결·클라이언트 설정 여부 포함)."""
    base = InstanceResponse.model_validate(instance)
    connected = bool(instance.oauth_access_token.strip())
    client_configured = bool(instance.oauth_client_id.strip() and instance.oauth_client_secret.strip())
    return base.model_copy(
        update={
            "oauth_connected": connected,
            "oauth_client_configured": client_configured,
            "oauth_client_id": instance.oauth_client_id,
            "oauth_redirect_uri": instance.oauth_redirect_uri,
            "oauth_scopes": instance.oauth_scopes,
        },
    )


async def _resolve_connect_client_config(
    session: AsyncSession,
    payload: OAuthConnectRequest,
) -> ZendeskOAuthClientConfig:
    """
    Client Credentials 연결 시 사용할 OAuth 클라이언트 설정을 결정한다.
    재연결(instance_id)이면 폼 입력을 우선하고, Secret만 비어 있으면 DB 값을 쓴다.
    """
    if payload.instance_id is None:
        try:
            return build_client_config(
                client_id=payload.oauth_client_id,
                client_secret=payload.oauth_client_secret,
                scopes=payload.oauth_scopes,
            )
        except ZendeskOAuthError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    instance = await session.get(Instance, payload.instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    if normalize_subdomain(instance.subdomain) != normalize_subdomain(payload.subdomain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="서브도메인이 인스턴스와 일치하지 않습니다.",
        )

    client_id = payload.oauth_client_id.strip() or instance.oauth_client_id.strip()
    client_secret = payload.oauth_client_secret.strip() or instance.oauth_client_secret.strip()
    scopes_raw = (payload.oauth_scopes or "").strip() or instance.oauth_scopes.strip()

    try:
        return build_client_config(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes_raw or None,
        )
    except ZendeskOAuthError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


async def _create_instance_with_brands(
    session: AsyncSession,
    *,
    subdomain: str,
    email: str,
    client_config,
    tokens: ZendeskOAuthTokens | None = None,
    name: str | None = None,
    selected_brand_ids: list[int] | None = None,
) -> InstanceDetailResponse:
    """OAuth 클라이언트·토큰·이메일로 인스턴스를 생성하고 브랜드를 저장한다."""
    normalized_subdomain = normalize_subdomain(subdomain)
    selected = set(selected_brand_ids or [])

    duplicate_query = select(Instance).where(
        Instance.subdomain == normalized_subdomain,
        Instance.email == email,
    )
    duplicate = await session.scalar(duplicate_query)
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 인스턴스입니다.",
        )

    instance = Instance(
        name=resolve_instance_name(name, normalized_subdomain),
        subdomain=normalized_subdomain,
        email=email,
        oauth_access_token="",
        oauth_refresh_token="",
        role=INSTANCE_ROLE,
        is_active=True,
    )
    apply_client_config_to_instance(instance, client_config)
    session.add(instance)
    await session.flush()

    if tokens is not None:
        ZendeskOAuthService.apply_tokens_to_instance(instance, tokens)

    try:
        zendesk_brands = await ZendeskOAuthService.get_brands(session, instance)
    except (ZendeskClientError, ZendeskOAuthError) as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    brand_rows: list[Brand] = []
    for brand in zendesk_brands:
        is_selected = brand.id in selected if selected else True
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
        **to_instance_response(instance).model_dump(),
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


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"message": "instances router is ready"}


@router.post("/oauth/connect", response_model=InstanceDetailResponse)
async def connect_oauth_client_credentials(
    payload: OAuthConnectRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceDetailResponse:
    """Client Credentials로 토큰을 발급하고 인스턴스를 생성하거나 갱신한다."""
    normalized = normalize_subdomain(payload.subdomain)
    try:
        client_config = await _resolve_connect_client_config(session, payload)
        tokens = await ZendeskOAuthService.exchange_client_credentials(
            subdomain=normalized,
            client_config=client_config,
        )
        profile = await ZendeskOAuthService.fetch_user_profile(
            subdomain=normalized,
            access_token=tokens.access_token,
        )
    except ZendeskOAuthError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if payload.instance_id is not None and payload.instance_id > 0:
        instance = await session.get(Instance, payload.instance_id)
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")
        if normalize_subdomain(instance.subdomain) != normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="서브도메인이 인스턴스와 일치하지 않습니다.",
            )
        apply_client_config_to_instance(instance, client_config)
        ZendeskOAuthService.apply_tokens_to_instance(instance, tokens)
        instance.email = profile.email
        if payload.name:
            instance.name = resolve_instance_name(payload.name, normalized)
        await session.commit()
        await session.refresh(instance)
        brands_query = select(Brand).where(Brand.instance_id == instance.id).order_by(Brand.name.asc())
        brands = (await session.execute(brands_query)).scalars().all()
        return InstanceDetailResponse(
            **to_instance_response(instance).model_dump(),
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

    return await _create_instance_with_brands(
        session,
        subdomain=normalized,
        email=profile.email,
        client_config=client_config,
        tokens=tokens,
        name=payload.name,
        selected_brand_ids=payload.selected_brand_ids,
    )


@router.post("/brands/preview", response_model=list[SourceBrandResponse])
async def preview_instance_brands(
    payload: SourceBrandPreviewRequest,
    session: AsyncSession = Depends(get_async_session),
) -> list[SourceBrandResponse]:
    instance = await session.get(Instance, payload.instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    try:
        brands = await ZendeskOAuthService.get_brands(session, instance)
    except (ZendeskClientError, ZendeskOAuthError) as error:
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


@router.post("/source/brands/preview", response_model=list[SourceBrandResponse])
async def preview_source_brands(
    payload: SourceBrandPreviewRequest,
    session: AsyncSession = Depends(get_async_session),
) -> list[SourceBrandResponse]:
    return await preview_instance_brands(payload, session)


@router.get("", response_model=list[InstanceResponse])
async def list_instances(session: AsyncSession = Depends(get_async_session)) -> list[InstanceResponse]:
    query = select(Instance).order_by(Instance.created_at.desc())
    result = await session.execute(query)
    instances = result.scalars().all()
    return [to_instance_response(instance) for instance in instances]


@router.get("/{instance_id}", response_model=InstanceDetailResponse)
async def get_instance(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceDetailResponse:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    brands_query = select(Brand).where(Brand.instance_id == instance.id).order_by(Brand.name.asc())
    brands = (await session.execute(brands_query)).scalars().all()

    return InstanceDetailResponse(
        **to_instance_response(instance).model_dump(),
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
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    if payload.name is not None:
        instance.name = resolve_instance_name(payload.name, instance.subdomain)

    if payload.email is not None:
        normalized_email = payload.email.strip()
        if not normalized_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="연결 계정(이메일)을 입력하세요.",
            )
        if normalized_email != instance.email:
            duplicate_query = select(Instance).where(
                Instance.subdomain == instance.subdomain,
                Instance.email == normalized_email,
                Instance.id != instance_id,
            )
            duplicate = await session.scalar(duplicate_query)
            if duplicate is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="같은 서브도메인에 동일 이메일 인스턴스가 이미 있습니다.",
                )
            instance.email = normalized_email

    if payload.oauth_client_id is not None and payload.oauth_client_id.strip():
        instance.oauth_client_id = payload.oauth_client_id.strip()
    if payload.oauth_client_secret is not None and payload.oauth_client_secret.strip():
        instance.oauth_client_secret = payload.oauth_client_secret.strip()
    if payload.oauth_scopes is not None:
        instance.oauth_scopes = payload.oauth_scopes.strip()

    await session.commit()
    await session.refresh(instance)
    return to_instance_response(instance)


@router.patch("/{instance_id}/active", response_model=InstanceResponse)
async def update_instance_active(
    instance_id: int,
    payload: UpdateInstanceActiveRequest,
    session: AsyncSession = Depends(get_async_session),
) -> InstanceResponse:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    instance.is_active = payload.is_active
    await session.commit()
    await session.refresh(instance)
    return to_instance_response(instance)


@router.post("/{instance_id}/connection-test", response_model=ConnectionTestResponse)
async def test_instance_connection(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> ConnectionTestResponse:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    try:
        config_from_instance(instance)
        await ZendeskOAuthService.get_brands(session, instance)
    except (ZendeskClientError, ZendeskOAuthError) as error:
        return ConnectionTestResponse(success=False, message=str(error))

    return ConnectionTestResponse(success=True, message="OAuth 연결 테스트에 성공했습니다.")


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
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
