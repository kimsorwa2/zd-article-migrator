"""Zendesk API 프록시 path 검증·URL 조립 단위 테스트."""

import pytest

from services.zendesk_proxy_service import (
    ZendeskProxyValidationError,
    build_zendesk_url,
    validate_proxy_path,
)


def test_validate_proxy_path_accepts_api_v2_path() -> None:
    assert validate_proxy_path("/api/v2/users/me.json") == "/api/v2/users/me.json"


def test_validate_proxy_path_rejects_non_api_v2() -> None:
    with pytest.raises(ZendeskProxyValidationError):
        validate_proxy_path("/admin/secret")


def test_validate_proxy_path_rejects_traversal() -> None:
    with pytest.raises(ZendeskProxyValidationError):
        validate_proxy_path("/api/v2/../admin")


def test_validate_proxy_path_rejects_query_in_path() -> None:
    with pytest.raises(ZendeskProxyValidationError):
        validate_proxy_path("/api/v2/tickets.json?page=1")


def test_build_zendesk_url_with_query() -> None:
    url = build_zendesk_url(
        "mycompany",
        "/api/v2/tickets.json",
        {"page[size]": "25", "sort_by": "updated_at"},
    )
    assert url == "https://mycompany.zendesk.com/api/v2/tickets.json?page%5Bsize%5D=25&sort_by=updated_at"


def test_build_zendesk_url_strips_zendesk_domain_suffix() -> None:
    url = build_zendesk_url("mycompany.zendesk.com", "/api/v2/brands.json", None)
    assert url == "https://mycompany.zendesk.com/api/v2/brands.json"
