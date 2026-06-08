from __future__ import annotations

import asyncio
import json as jsonlib
import time
from typing import Any, Literal
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instance
from services.zendesk_client import ZendeskClient
from services.zendesk_oauth_credentials import ZendeskOAuthError, config_from_instance
from services.zendesk_oauth_service import ZendeskOAuthService


MAX_PROXY_BODY_BYTES = 512 * 1024
ALLOWED_PROXY_PATH_PREFIX = "/api/v2/"
PROXY_REQUEST_TIMEOUT_SECONDS = 20.0

RESPONSE_HEADER_ALLOWLIST = (
    "content-type",
    "x-rate-limit",
    "x-rate-limit-remaining",
    "retry-after",
    "x-zendesk-request-id",
    "x-idempotency-lookup",
)


class ZendeskProxyValidationError(ValueError):
    """프록시 요청 path·본문 검증 실패."""


BLOCKED_PROXY_HEADER_NAMES = frozenset({"authorization", "host", "content-length"})


def sanitize_proxy_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """
    OAuth·전송 계층 헤더를 덮어쓰지 않도록 사용자 헤더를 정제한다.

    @param headers 사용자 지정 HTTP 헤더
    @returns 안전한 헤더 dict
    """
    if not headers:
        return {}
    safe: dict[str, str] = {}
    for key, value in headers.items():
        normalized_key = key.strip()
        if not normalized_key or normalized_key.lower() in BLOCKED_PROXY_HEADER_NAMES:
            continue
        safe[normalized_key] = value
    return safe


def validate_proxy_body(json_body: dict[str, Any] | None, raw_body: str | None) -> None:
    """JSON 본문과 Raw 본문이 동시에 지정되지 않았는지 검증한다."""
    if json_body is not None and raw_body is not None and raw_body.strip():
        raise ZendeskProxyValidationError("json_body와 raw_body를 동시에 지정할 수 없습니다.")


def validate_proxy_path(path: str) -> str:
    """
    Zendesk Support API path가 안전한지 검증한다.

    @param path /api/v2/... 형태의 경로
    @returns 공백 제거된 path
    @raises ZendeskProxyValidationError 허용되지 않은 path
    """
    normalized = path.strip()
    if not normalized.startswith(ALLOWED_PROXY_PATH_PREFIX):
        raise ZendeskProxyValidationError("/api/v2/ 로 시작하는 경로만 허용됩니다.")
    if "?" in normalized or "#" in normalized:
        raise ZendeskProxyValidationError("path에 쿼리스트링·해시를 포함할 수 없습니다.")
    if ".." in normalized or "//" in normalized:
        raise ZendeskProxyValidationError("path에 .. 또는 // 를 포함할 수 없습니다.")
    if normalized.startswith("http://") or normalized.startswith("https://"):
        raise ZendeskProxyValidationError("전체 URL은 허용되지 않습니다. path만 입력하세요.")
    return normalized


def build_zendesk_url(
    subdomain: str,
    path: str,
    query_params: dict[str, str] | None,
) -> str:
    """
    인스턴스 subdomain과 path로 Zendesk API 전체 URL을 조립한다.

    @param subdomain Zendesk 서브도메인
    @param path 검증된 API path
    @param query_params 선택적 쿼리 파라미터
    @returns https://{subdomain}.zendesk.com/api/v2/... URL
    """
    safe_path = validate_proxy_path(path)
    host = subdomain.strip().replace(".zendesk.com", "")
    base = f"https://{host}.zendesk.com{safe_path}"
    if not query_params:
        return base
    return f"{base}?{urlencode(query_params)}"


def _validate_json_body_size(json_body: dict[str, Any] | None) -> None:
    """요청 JSON 본문 크기 상한을 검증한다."""
    if json_body is None:
        return
    encoded = jsonlib.dumps(json_body, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_PROXY_BODY_BYTES:
        raise ZendeskProxyValidationError(
            f"요청 본문이 너무 큽니다. 최대 {MAX_PROXY_BODY_BYTES // 1024}KB까지 허용됩니다."
        )


def _pick_response_headers(response: httpx.Response) -> dict[str, str]:
    """응답 헤더 중 디버깅에 유용한 항목만 추린다."""
    picked: dict[str, str] = {}
    for key, value in response.headers.items():
        if key.lower() in RESPONSE_HEADER_ALLOWLIST:
            picked[key] = value
    return picked


def _parse_response_body(response: httpx.Response) -> Any:
    """HTTP 응답 본문을 JSON 또는 문자열로 파싱한다."""
    if response.status_code == 204 or not (response.content or b"").strip():
        return None
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def _build_error_message(response: httpx.Response) -> str:
    """Zendesk 오류 응답에서 사용자 메시지를 추출한다."""
    body = _parse_response_body(response)
    if isinstance(body, dict):
        detail = body.get("error") or body.get("description") or body.get("message") or body.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return ZendeskClient._build_error_summary(response)


async def _execute_http_request(
    *,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    url: str,
    access_token: str,
    json_body: dict[str, Any] | None,
    raw_body: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    """
    OAuth Bearer로 Zendesk API HTTP 요청을 수행한다(4xx도 Response 반환).

    @param method HTTP 메서드
    @param url 전체 요청 URL
    @param access_token Bearer access token
    @param json_body JSON 본문
    @param raw_body Raw 문자열 본문
    @param extra_headers 추가 HTTP 헤더
    @returns httpx Response
    """
    headers = ZendeskClient._build_headers(access_token=access_token)
    headers.update(sanitize_proxy_headers(extra_headers))
    async with httpx.AsyncClient(timeout=PROXY_REQUEST_TIMEOUT_SECONDS) as client:
        await asyncio.sleep(0.5)
        if raw_body is not None and raw_body != "":
            return await client.request(
                method=method,
                url=url,
                headers=headers,
                content=raw_body.encode("utf-8"),
            )
        return await client.request(method=method, url=url, headers=headers, json=json_body)


class ZendeskProxyService:
    """Zendesk Support API 프록시 호출 서비스."""

    @staticmethod
    def _ensure_oauth_connected(instance: Instance) -> None:
        """OAuth 연결 여부를 검증한다."""
        if not (instance.oauth_access_token or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth 연결이 필요합니다. 인스턴스 관리에서 Zendesk OAuth를 연결하세요.",
            )
        try:
            config_from_instance(instance)
        except ZendeskOAuthError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @classmethod
    async def execute_request(
        cls,
        session: AsyncSession,
        *,
        instance: Instance,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        path: str,
        json_body: dict[str, Any] | None = None,
        raw_body: str | None = None,
        query_params: dict[str, str] | None = None,
        request_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        인스턴스 OAuth로 Zendesk API 프록시 요청을 실행한다.

        @param session DB 세션
        @param instance Zendesk 인스턴스
        @param method HTTP 메서드
        @param path /api/v2/... 경로
        @param json_body JSON 요청 본문
        @param raw_body Raw 문자열 요청 본문
        @param query_params 쿼리 파라미터
        @param request_headers 추가 HTTP 헤더
        @returns 프록시 응답 dict (success, http_status, body 등)
        """
        cls._ensure_oauth_connected(instance)

        try:
            _validate_json_body_size(json_body)
            validate_proxy_body(json_body, raw_body)
            request_url = build_zendesk_url(instance.subdomain, path, query_params)
        except ZendeskProxyValidationError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

        normalized_raw_body = raw_body if raw_body is not None and raw_body.strip() else None
        safe_headers = sanitize_proxy_headers(request_headers)

        started = time.perf_counter()

        try:
            access_token = await ZendeskOAuthService.get_access_token(session, instance)
            response = await _execute_http_request(
                method=method,
                url=request_url,
                access_token=access_token,
                json_body=json_body,
                raw_body=normalized_raw_body,
                extra_headers=safe_headers,
            )

            # 401/403이면 토큰 재발급 후 1회 재시도
            if response.status_code in (401, 403):
                access_token = await ZendeskOAuthService.reissue_instance_access_token(session, instance)
                response = await _execute_http_request(
                    method=method,
                    url=request_url,
                    access_token=access_token,
                    json_body=json_body,
                    raw_body=normalized_raw_body,
                    extra_headers=safe_headers,
                )
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Zendesk API 연결 실패: {error}",
            ) from error
        except ZendeskOAuthError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

        latency_ms = int((time.perf_counter() - started) * 1000)
        response_body = _parse_response_body(response)
        http_status = response.status_code
        success = 200 <= http_status < 300

        return {
            "success": success,
            "http_status": http_status,
            "latency_ms": latency_ms,
            "request_url": request_url,
            "response_body": response_body,
            "response_headers": _pick_response_headers(response),
            "error_message": None if success else _build_error_message(response),
        }
