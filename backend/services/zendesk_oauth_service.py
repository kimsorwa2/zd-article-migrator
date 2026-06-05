from __future__ import annotations



import logging

import time

from dataclasses import dataclass

from typing import Any, Literal



import httpx

from sqlalchemy.ext.asyncio import AsyncSession



from db.models import Instance

from services.zendesk_client import ZendeskClient, ZendeskClientError

from services.zendesk_oauth_credentials import (

    ZendeskOAuthClientConfig,

    ZendeskOAuthError,

    apply_client_config_to_instance,

    config_from_instance,

)



logger = logging.getLogger(__name__)



TOKEN_REQUEST_TIMEOUT_SECONDS = 20.0

# access_token 만료 전 선제 재발급 여유(초). Zendesk 기본 만료(예: 30분) 대비 버퍼.

TOKEN_EXPIRY_BUFFER_SECONDS = 120





@dataclass(slots=True)

class ZendeskOAuthTokens:

    """

    /**

     * Client Credentials로 발급받은 access token.

     * @param {str} access_token API Bearer 토큰

     * @param {int | None} expires_in 유효 기간(초). 없으면 만료 시각 미저장

     */

    """



    access_token: str

    expires_in: int | None = None





@dataclass(slots=True)

class ZendeskOAuthUserProfile:

    """

    /**

     * OAuth 클라이언트 연결 사용자(/users/me) 정보.

     * Client Credentials 토큰은 OAuth 클라이언트 생성자 계정으로 동작한다.

     */

    """



    email: str

    name: str | None = None





class ZendeskOAuthService:

    """

    /**

     * Zendesk Client Credentials OAuth 및 토큰 만료 시 재발급을 담당한다.

     * @see https://developer.zendesk.com/api-reference/ticketing/oauth/grant_type_tokens/#client-credentials-grant-type

     */

    """



    @staticmethod

    def _zendesk_base_url(subdomain: str) -> str:

        return f"https://{subdomain.strip().replace('.zendesk.com', '')}.zendesk.com"



    @classmethod

    async def exchange_client_credentials(

        cls,

        *,

        subdomain: str,

        client_config: ZendeskOAuthClientConfig,

    ) -> ZendeskOAuthTokens:

        """

        /**

         * client_id·client_secret으로 access token을 발급받는다(refresh_token 없음).

         * @param {str} subdomain Zendesk 서브도메인

         * @param {ZendeskOAuthClientConfig} client_config OAuth 클라이언트

         * @returns {ZendeskOAuthTokens} access token

         */

        """

        body = {

            "grant_type": "client_credentials",

            "client_id": client_config.client_id,

            "client_secret": client_config.client_secret,

            "scope": client_config.scopes,

        }

        return await cls._post_token_endpoint(subdomain=subdomain, json_body=body)



    @classmethod

    async def _post_token_endpoint(cls, *, subdomain: str, json_body: dict[str, str]) -> ZendeskOAuthTokens:

        url = f"{cls._zendesk_base_url(subdomain)}/oauth/tokens"

        async with httpx.AsyncClient(timeout=TOKEN_REQUEST_TIMEOUT_SECONDS) as client:

            response = await client.post(url, json=json_body)



        if response.status_code >= 400:

            detail = response.text.strip()[:400]

            if response.status_code == 400 and "invalid_client" in detail.lower():

                raise ZendeskOAuthError(

                    "OAuth Client Identifier·Secret이 올바르지 않습니다. Admin Center 설정을 확인하세요.",

                )

            if response.status_code == 400 and "invalid_grant" in detail:

                raise ZendeskOAuthError(

                    "OAuth 토큰 발급이 거부되었습니다. confidential OAuth 클라이언트인지 확인하세요.",

                )

            raise ZendeskOAuthError(f"OAuth 토큰 요청 실패 (HTTP {response.status_code}): {detail}")



        try:

            payload = response.json()

        except ValueError as error:

            raise ZendeskOAuthError("OAuth 토큰 응답 JSON 파싱에 실패했습니다.") from error



        access = payload.get("access_token")

        if not isinstance(access, str) or not access.strip():

            raise ZendeskOAuthError("OAuth 응답에 access_token이 없습니다.")



        expires_raw = payload.get("expires_in")

        expires_in: int | None = None

        if isinstance(expires_raw, int) and expires_raw > 0:

            expires_in = expires_raw

        elif isinstance(expires_raw, str) and expires_raw.isdigit():

            expires_in = int(expires_raw)



        return ZendeskOAuthTokens(access_token=access.strip(), expires_in=expires_in)



    @classmethod

    async def fetch_user_profile(cls, *, subdomain: str, access_token: str) -> ZendeskOAuthUserProfile:

        """

        /**

         * Bearer 토큰으로 /users/me 를 조회해 이메일·이름을 가져온다.

         * Client Credentials에서는 OAuth 클라이언트 생성자 프로필이 반환된다.

         */

        """

        url = f"{cls._zendesk_base_url(subdomain)}/api/v2/users/me.json"

        payload = await ZendeskClient.get_json(url=url, access_token=access_token)

        user = payload.get("user")

        if not isinstance(user, dict):

            raise ZendeskOAuthError("Zendesk /users/me 응답 형식이 올바르지 않습니다.")



        email = user.get("email")

        if not isinstance(email, str) or not email.strip():

            raise ZendeskOAuthError("Zendesk 사용자 이메일을 확인할 수 없습니다.")



        name = user.get("name")

        return ZendeskOAuthUserProfile(

            email=email.strip(),

            name=name.strip() if isinstance(name, str) and name.strip() else None,

        )



    @classmethod

    def _token_expires_at_unix(cls, instance: Instance) -> int | None:

        """DB에 저장된 access token 만료 시각(Unix 초)을 반환한다."""

        raw = (instance.oauth_token_expires_at or "").strip()

        if not raw.isdigit():

            return None

        return int(raw)



    @classmethod

    def _is_access_token_expired(cls, instance: Instance) -> bool:

        """저장된 만료 시각 기준으로 access token이 곧 만료되었는지 판단한다."""

        expires_at = cls._token_expires_at_unix(instance)

        if expires_at is None:

            return False

        return expires_at <= int(time.time()) + TOKEN_EXPIRY_BUFFER_SECONDS



    @classmethod

    def apply_tokens_to_instance(cls, instance: Instance, tokens: ZendeskOAuthTokens) -> None:

        """

        /**

         * Instance 행에 access token·만료 시각을 반영한다(커밋은 호출자가 수행).

         * Client Credentials는 refresh_token을 사용하지 않는다.

         */

        """

        instance.oauth_access_token = tokens.access_token

        instance.oauth_refresh_token = ""

        if tokens.expires_in is not None:

            instance.oauth_token_expires_at = str(int(time.time()) + tokens.expires_in)

        else:

            instance.oauth_token_expires_at = ""



    @classmethod

    async def reissue_instance_access_token(cls, session: AsyncSession, instance: Instance) -> str:

        """

        /**

         * client_credentials로 access token을 재발급하고 DB에 저장한다.

         * @param {AsyncSession} session DB 세션

         * @param {Instance} instance 대상 인스턴스

         * @returns {str} 새 access_token

         */

        """

        client_config = config_from_instance(instance)

        tokens = await cls.exchange_client_credentials(

            subdomain=instance.subdomain,

            client_config=client_config,

        )

        cls.apply_tokens_to_instance(instance, tokens)

        await session.flush()

        logger.info("Zendesk OAuth access token 재발급 완료 instance_id=%s", instance.id)

        return tokens.access_token



    @classmethod

    async def ensure_valid_access_token(cls, session: AsyncSession, instance: Instance) -> str:

        """

        /**

         * 저장된 토큰이 없거나 만료 임박이면 재발급 후 access_token을 반환한다.

         */

        """

        if not instance.oauth_access_token.strip():

            raise ZendeskOAuthError(

                f"인스턴스 「{instance.name}」에 OAuth 연결이 없습니다. 인스턴스 관리에서 Zendesk를 연결해 주세요.",

            )

        if cls._is_access_token_expired(instance):

            return await cls.reissue_instance_access_token(session, instance)

        return instance.oauth_access_token



    @classmethod

    async def get_access_token(cls, session: AsyncSession, instance: Instance) -> str:

        """인스턴스에 유효한 access_token을 반환한다(만료 임박 시 선제 재발급)."""

        return await cls.ensure_valid_access_token(session, instance)



    @classmethod

    def _is_unauthorized(cls, error: ZendeskClientError) -> bool:

        message = str(error)

        return "status=401" in message or "status=403" in message



    @classmethod

    async def _retry_after_reissue(

        cls,

        session: AsyncSession,

        instance: Instance,

        operation: Literal["request_json", "delete", "get_bytes", "upload_attachment"],

        *,

        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None,

        url: str | None = None,

        json_body: dict[str, Any] | None = None,

        upload_kwargs: dict[str, Any] | None = None,

    ) -> dict[str, Any] | bytes | None:

        access_token = await cls.reissue_instance_access_token(session, instance)

        if operation == "request_json" and method is not None and url is not None:

            return await ZendeskClient.request_json(

                method=method,

                url=url,

                access_token=access_token,

                json=json_body,

            )

        if operation == "delete" and url is not None:

            await ZendeskClient.delete(url=url, access_token=access_token)

            return None

        if operation == "get_bytes" and url is not None:

            return await ZendeskClient.get_bytes(url=url, access_token=access_token)

        if operation == "upload_attachment" and upload_kwargs is not None:

            return await ZendeskClient.upload_attachment(access_token=access_token, **upload_kwargs)

        raise ZendeskOAuthError("내부 재시도 인자가 올바르지 않습니다.")



    @classmethod

    async def request_json(

        cls,

        session: AsyncSession,

        instance: Instance,

        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],

        url: str,

        *,

        json_body: dict[str, Any] | None = None,

    ) -> dict[str, Any]:

        """

        /**

         * OAuth Bearer로 Zendesk JSON API를 호출한다.

         * 401/403 시 client_credentials 재발급 후 1회 재시도한다.

         */

        """

        access_token = await cls.get_access_token(session, instance)

        try:

            return await ZendeskClient.request_json(

                method=method,

                url=url,

                access_token=access_token,

                json=json_body,

            )

        except ZendeskClientError as error:

            if not cls._is_unauthorized(error):

                raise

            result = await cls._retry_after_reissue(

                session,

                instance,

                "request_json",

                method=method,

                url=url,

                json_body=json_body,

            )

            assert isinstance(result, dict)

            return result



    @classmethod

    async def get_json(cls, session: AsyncSession, instance: Instance, url: str) -> dict[str, Any]:

        """GET JSON 단축 호출."""

        return await cls.request_json(session, instance, "GET", url)



    @classmethod

    async def post_json(

        cls,

        session: AsyncSession,

        instance: Instance,

        url: str,

        json_body: dict[str, Any],

    ) -> dict[str, Any]:

        """POST JSON 단축 호출."""

        return await cls.request_json(session, instance, "POST", url, json_body=json_body)



    @classmethod

    async def put_json(

        cls,

        session: AsyncSession,

        instance: Instance,

        url: str,

        json_body: dict[str, Any],

    ) -> dict[str, Any]:

        """PUT JSON 단축 호출."""

        return await cls.request_json(session, instance, "PUT", url, json_body=json_body)



    @classmethod

    async def patch_json(

        cls,

        session: AsyncSession,

        instance: Instance,

        url: str,

        json_body: dict[str, Any],

    ) -> dict[str, Any]:

        """PATCH JSON 단축 호출."""

        return await cls.request_json(session, instance, "PATCH", url, json_body=json_body)



    @classmethod

    async def delete(cls, session: AsyncSession, instance: Instance, url: str) -> None:

        """DELETE 호출(401/403 시 재발급 후 재시도)."""

        access_token = await cls.get_access_token(session, instance)

        try:

            await ZendeskClient.delete(url=url, access_token=access_token)

        except ZendeskClientError as error:

            if not cls._is_unauthorized(error):

                raise

            await cls._retry_after_reissue(session, instance, "delete", url=url)



    @classmethod

    async def get_bytes(cls, session: AsyncSession, instance: Instance, url: str) -> bytes:

        """GET 바이너리(401/403 시 재발급 후 재시도)."""

        access_token = await cls.get_access_token(session, instance)

        try:

            return await ZendeskClient.get_bytes(url=url, access_token=access_token)

        except ZendeskClientError as error:

            if not cls._is_unauthorized(error):

                raise

            result = await cls._retry_after_reissue(session, instance, "get_bytes", url=url)

            assert isinstance(result, bytes)

            return result



    @classmethod

    async def upload_attachment(

        cls,

        session: AsyncSession,

        instance: Instance,

        *,

        article_id: int,

        filename: str,

        content_type: str,

        content: bytes,

        target_subdomain: str,

    ) -> dict[str, Any]:

        """아티클 첨부 업로드(401/403 시 재발급 후 재시도)."""

        upload_kwargs = {

            "article_id": article_id,

            "filename": filename,

            "content_type": content_type,

            "content": content,

            "target_subdomain": target_subdomain,

        }

        access_token = await cls.get_access_token(session, instance)

        try:

            return await ZendeskClient.upload_attachment(

                access_token=access_token,

                **upload_kwargs,

            )

        except ZendeskClientError as error:

            if not cls._is_unauthorized(error):

                raise

            result = await cls._retry_after_reissue(

                session,

                instance,

                "upload_attachment",

                upload_kwargs=upload_kwargs,

            )

            assert isinstance(result, dict)

            return result



    @classmethod

    async def get_brands(cls, session: AsyncSession, instance: Instance) -> list:

        """인스턴스 OAuth 토큰으로 브랜드 목록을 조회한다."""

        return await ZendeskClient.get_brands(

            main_subdomain=instance.subdomain,

            access_token=await cls.get_access_token(session, instance),

        )


