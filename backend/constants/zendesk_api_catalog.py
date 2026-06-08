from __future__ import annotations

from constants.zendesk_api_catalog_types import (
    ZendeskApiOperation,
    ZendeskApiProduct,
    build_categories_from_operations,
)
from constants.zendesk_custom_data_api_catalog import (
    CUSTOM_DATA_API_OPERATIONS,
    PRODUCT_DOC_URL as CUSTOM_DATA_DOC_URL,
)
from constants.zendesk_help_center_api_catalog import (
    HELP_CENTER_API_OPERATIONS,
    PRODUCT_DOC_URL as HELP_CENTER_DOC_URL,
)
from constants.zendesk_omnichannel_api_catalog import (
    OMNICHANNEL_API_OPERATIONS,
    PRODUCT_DOC_URL as OMNICHANNEL_DOC_URL,
)
from constants.zendesk_ticketing_api_catalog import (
    PRODUCT_DOC_URL as TICKETING_DOC_URL,
    TICKETING_API_OPERATIONS,
)
from constants.zendesk_voice_tpe_api_catalog import (
    PRODUCT_DOC_URL as VOICE_TPE_DOC_URL,
    VOICE_TPE_API_OPERATIONS,
)


def _build_product(
    product_id: str,
    label: str,
    doc_url: str,
    operations: tuple[ZendeskApiOperation, ...],
) -> ZendeskApiProduct:
    """
    product 메타와 operation 튜플로 카탈로그 product 노드를 생성한다.

    @param product_id product 식별자
    @param label UI 표시명
    @param doc_url 공식 소개 문서 URL
    @param operations 해당 product operation 목록
    @returns ZendeskApiProduct
    """
    return ZendeskApiProduct(
        id=product_id,
        label=label,
        doc_url=doc_url,
        categories=build_categories_from_operations(operations),
    )


def build_zendesk_api_catalog() -> tuple[ZendeskApiProduct, ...]:
    """
    Zendesk API Request 콘솔용 통합 카탈로그를 반환한다.

    @returns Ticketing·Help Center·Voice(TPE)·Custom Data·Omnichannel product 목록
    """
    return (
        _build_product("ticketing", "Ticketing", TICKETING_DOC_URL, TICKETING_API_OPERATIONS),
        _build_product("help-center", "Help Center", HELP_CENTER_DOC_URL, HELP_CENTER_API_OPERATIONS),
        _build_product("voice-tpe", "Voice (TPE)", VOICE_TPE_DOC_URL, VOICE_TPE_API_OPERATIONS),
        _build_product("custom-data", "Custom Data", CUSTOM_DATA_DOC_URL, CUSTOM_DATA_API_OPERATIONS),
        _build_product("omnichannel", "Omnichannel", OMNICHANNEL_DOC_URL, OMNICHANNEL_API_OPERATIONS),
    )
