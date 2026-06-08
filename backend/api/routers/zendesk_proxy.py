from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ZendeskApiCatalogResponse,
    ZendeskApiCategoryResponse,
    ZendeskApiGroupResponse,
    ZendeskApiOperationResponse,
    ZendeskApiProductResponse,
    ZendeskProxyRequest,
    ZendeskProxyResponse,
)
from constants.zendesk_api_catalog import build_zendesk_api_catalog
from db.database import get_async_session
from db.models import Instance
from services.zendesk_proxy_service import ZendeskProxyService

router = APIRouter(prefix="/zendesk-proxy", tags=["zendesk-proxy"])


def _to_catalog_response() -> ZendeskApiCatalogResponse:
    """코드 상수 카탈로그를 API 응답 모델로 변환한다."""
    products = []
    for product in build_zendesk_api_catalog():
        categories = []
        for category in product.categories:
            groups = []
            for group in category.groups:
                operations = [
                    ZendeskApiOperationResponse(
                        id=operation.id,
                        category=operation.category,
                        group=operation.group,
                        label=operation.label,
                        method=operation.method,
                        path_template=operation.path_template,
                        path_params=list(operation.path_params),
                        doc_url=operation.doc_url,
                        sample_body=operation.sample_body,
                        default_query=operation.default_query,
                    )
                    for operation in group.operations
                ]
                groups.append(
                    ZendeskApiGroupResponse(
                        id=group.id,
                        label=group.label,
                        operations=operations,
                    )
                )
            categories.append(
                ZendeskApiCategoryResponse(
                    id=category.id,
                    label=category.label,
                    groups=groups,
                )
            )
        products.append(
            ZendeskApiProductResponse(
                id=product.id,
                label=product.label,
                doc_url=product.doc_url,
                categories=categories,
            )
        )
    return ZendeskApiCatalogResponse(products=products)


@router.get("/catalog", response_model=ZendeskApiCatalogResponse)
async def get_zendesk_api_catalog() -> ZendeskApiCatalogResponse:
    """
    Zendesk API 카탈로그(Ticketing·Help Center·Voice TPE·Custom Data·Omnichannel)를 반환한다.

    @returns 문서 사이드바 구조의 API 목록
    """
    return _to_catalog_response()


@router.post("/request", response_model=ZendeskProxyResponse)
async def proxy_zendesk_request(
    payload: ZendeskProxyRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ZendeskProxyResponse:
    """
    등록된 인스턴스 OAuth로 Zendesk API 요청을 프록시한다.

    @param payload 프록시 요청 본문
    @returns Zendesk HTTP 상태·본문·지연 시간
    """
    instance = await session.get(Instance, payload.instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인스턴스를 찾을 수 없습니다.")

    result = await ZendeskProxyService.execute_request(
        session,
        instance=instance,
        method=payload.method,
        path=payload.path,
        json_body=payload.json_body,
        raw_body=payload.raw_body,
        query_params=payload.query_params,
        request_headers=payload.request_headers,
    )
    return ZendeskProxyResponse(**result)
