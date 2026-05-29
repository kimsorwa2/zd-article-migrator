from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any, Literal

import httpx


REQUEST_TIMEOUT_SECONDS = 20.0
REQUEST_INTERVAL_SECONDS = 0.5
MAX_RETRY_COUNT = 3


class ZendeskClientError(Exception):
    """Zendesk API 호출 실패 시 사용하는 예외."""


@dataclass(slots=True)
class ZendeskBrand:
    """
    /**
     * Zendesk 브랜드 정보를 표현한다.
     * @param {int} id Zendesk 브랜드 ID
     * @param {str} name 브랜드 이름
     * @param {str} subdomain 브랜드 서브도메인
     * @returns {None} 데이터 모델이므로 반환값 없음
     */
    """

    id: int
    name: str
    subdomain: str
    has_help_center: bool


class ZendeskClient:
    """
    /**
     * Zendesk API 공통 통신 기능을 제공한다.
     * @returns {None} 유틸리티 클래스이므로 반환값 없음
     */
    """

    @staticmethod
    def _build_error_summary(response: httpx.Response) -> str:
        """
        /**
         * 실패 응답에서 로그/에러 메시지용 요약 문자열을 생성한다.
         * @param {httpx.Response} response HTTP 응답 객체
         * @returns {str} 상태 코드와 핵심 메시지를 담은 요약 문자열
         */
        """
        fallback = response.reason_phrase or "unknown error"
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return fallback

        try:
            payload = response.json()
        except ValueError:
            return fallback

        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("description") or payload.get("message") or payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()

        return fallback

    @staticmethod
    def _build_headers(email: str, api_token: str) -> dict[str, str]:
        """
        /**
         * Basic Auth 헤더를 생성한다.
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {dict[str, str]} 인증 헤더가 포함된 헤더 딕셔너리
         */
        """
        credential = f"{email}/token:{api_token}"
        encoded = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}

    @classmethod
    async def _request(
        cls,
        method: Literal["GET", "POST", "PATCH", "DELETE"],
        url: str,
        email: str,
        api_token: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response:
        """
        /**
         * Zendesk API 공통 요청을 수행하고 재시도 정책을 적용한다.
         * @param {"GET" | "POST" | "PATCH" | "DELETE"} method HTTP 메서드
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {dict[str, Any] | None} json 요청 본문(JSON)
         * @param {dict[str, str] | None} headers 추가 요청 헤더
         * @param {dict[str, tuple[str, bytes, str]] | None} files 멀티파트 파일 데이터
         * @returns {httpx.Response} HTTP 응답 객체
         */
        """
        request_headers = cls._build_headers(email=email, api_token=api_token)
        if files is not None and "Content-Type" in request_headers:
            # 멀티파트 업로드 시 Content-Type은 httpx가 자동으로 설정한다.
            request_headers.pop("Content-Type")
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            # Zendesk rate limit 대응을 위해 각 요청 전 고정 대기 시간을 둔다.
            await asyncio.sleep(REQUEST_INTERVAL_SECONDS)

            for attempt in range(MAX_RETRY_COUNT + 1):
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json,
                    files=files,
                )

                if response.status_code != 429:
                    break

                if attempt >= MAX_RETRY_COUNT:
                    raise ZendeskClientError("Zendesk API 요청이 429로 반복 실패했습니다. 잠시 후 다시 시도하세요.")

                retry_after_header = response.headers.get("Retry-After")
                retry_after_seconds = float(retry_after_header) if retry_after_header else REQUEST_INTERVAL_SECONDS
                await asyncio.sleep(retry_after_seconds)

            if response.status_code >= 400:
                error_summary = cls._build_error_summary(response)
                raise ZendeskClientError(
                    f"Zendesk API 요청 실패: method={method}, status={response.status_code}, url={url}, reason={error_summary}"
                )

            return response

    @classmethod
    async def request_json(
        cls,
        method: Literal["GET", "POST", "PATCH", "DELETE"],
        url: str,
        email: str,
        api_token: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        /**
         * Zendesk API 요청 후 JSON 응답을 딕셔너리로 반환한다.
         * @param {"GET" | "POST" | "PATCH" | "DELETE"} method HTTP 메서드
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {dict[str, Any] | None} json 요청 본문(JSON)
         * @returns {dict[str, Any]} 파싱된 JSON 응답
         */
        """
        response = await cls._request(
            method=method,
            url=url,
            email=email,
            api_token=api_token,
            json=json,
        )
        return response.json()

    @classmethod
    async def get_json(cls, url: str, email: str, api_token: str) -> dict[str, Any]:
        """
        /**
         * GET 요청으로 JSON 응답을 반환한다.
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {dict[str, Any]} 파싱된 JSON 응답
         */
        """
        return await cls.request_json(method="GET", url=url, email=email, api_token=api_token)

    @classmethod
    async def post_json(
        cls,
        url: str,
        email: str,
        api_token: str,
        json: dict[str, Any],
    ) -> dict[str, Any]:
        """
        /**
         * POST 요청으로 JSON 응답을 반환한다.
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {dict[str, Any]} json 요청 본문(JSON)
         * @returns {dict[str, Any]} 파싱된 JSON 응답
         */
        """
        return await cls.request_json(method="POST", url=url, email=email, api_token=api_token, json=json)

    @classmethod
    async def patch_json(
        cls,
        url: str,
        email: str,
        api_token: str,
        json: dict[str, Any],
    ) -> dict[str, Any]:
        """
        /**
         * PATCH 요청으로 JSON 응답을 반환한다.
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {dict[str, Any]} json 요청 본문(JSON)
         * @returns {dict[str, Any]} 파싱된 JSON 응답
         */
        """
        return await cls.request_json(method="PATCH", url=url, email=email, api_token=api_token, json=json)

    @classmethod
    async def delete(cls, url: str, email: str, api_token: str) -> None:
        """
        /**
         * DELETE 요청을 수행한다.
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {None} 성공 시 반환값 없음
         */
        """
        await cls._request(method="DELETE", url=url, email=email, api_token=api_token)

    @classmethod
    async def get_bytes(cls, url: str, email: str, api_token: str) -> bytes:
        """
        /**
         * GET 요청으로 바이너리 응답을 반환한다.
         * @param {str} url 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {bytes} 다운로드된 바이너리 데이터
         */
        """
        response = await cls._request(method="GET", url=url, email=email, api_token=api_token)
        return response.content

    @classmethod
    async def upload_attachment(
        cls,
        article_id: int,
        filename: str,
        content_type: str,
        content: bytes,
        target_subdomain: str,
        email: str,
        api_token: str,
    ) -> dict[str, Any]:
        """
        /**
         * 타겟 아티클에 첨부파일을 업로드한다.
         * @param {int} article_id 타겟 아티클 ID
         * @param {str} filename 업로드 파일명
         * @param {str} content_type MIME 타입
         * @param {bytes} content 업로드할 파일 바이너리
         * @param {str} target_subdomain 타겟 Zendesk 서브도메인
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {dict[str, Any]} 업로드 응답 JSON
         */
        """
        url = f"https://{target_subdomain}.zendesk.com/api/v2/help_center/articles/{article_id}/attachments"
        response = await cls._request(
            method="POST",
            url=url,
            email=email,
            api_token=api_token,
            files={"file": (filename, content, content_type)},
        )
        return response.json()

    @classmethod
    async def test_account(cls, subdomain: str, email: str, api_token: str) -> None:
        """
        /**
         * 타겟 또는 공통 계정의 연결 가능 여부를 확인한다.
         * @param {str} subdomain Zendesk 서브도메인
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {None} 성공 시 반환값 없음, 실패 시 예외 발생
         */
        """
        url = f"https://{subdomain}.zendesk.com/api/v2/account.json"
        await cls.get_json(url=url, email=email, api_token=api_token)

    @classmethod
    async def get_brands(cls, main_subdomain: str, email: str, api_token: str) -> list[ZendeskBrand]:
        """
        /**
         * 소스 인스턴스의 브랜드 목록을 조회한다.
         * @param {str} main_subdomain 소스 메인 서브도메인
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @returns {list[ZendeskBrand]} Zendesk 브랜드 목록
         */
        """
        url = f"https://{main_subdomain}.zendesk.com/api/v2/brands.json"
        payload = await cls.get_json(url=url, email=email, api_token=api_token)
        brands = payload.get("brands", [])

        # 응답 구조가 일부 다를 수 있어 안전하게 필드를 추출한다.
        return [
            ZendeskBrand(
                id=brand["id"],
                name=brand["name"],
                subdomain=brand.get("subdomain", main_subdomain),
                has_help_center=bool(brand.get("has_help_center", True)),
            )
            for brand in brands
        ]
