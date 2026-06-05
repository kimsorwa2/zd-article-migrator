from __future__ import annotations



from dataclasses import dataclass



from config.oauth_settings import default_oauth_scopes

from db.models import Instance





class ZendeskOAuthError(Exception):

    """Zendesk OAuth 설정·흐름 오류."""





@dataclass(slots=True, frozen=True)

class ZendeskOAuthClientConfig:

    """

    /**

     * Zendesk 인스턴스(서브도메인)별 OAuth 클라이언트 설정(Client Credentials용).

     * Admin Center confidential OAuth 클라이언트의 Identifier·Secret과 쌍을 이뤄야 한다.

     */

    """



    client_id: str

    client_secret: str

    scopes: str





def resolve_scopes(raw: str | None) -> str:

    """인스턴스·요청·앱 기본값 순으로 scope 문자열을 결정한다."""

    trimmed = (raw or "").strip()

    return trimmed if trimmed else default_oauth_scopes()





def build_client_config(

    *,

    client_id: str,

    client_secret: str,

    scopes: str | None = None,

) -> ZendeskOAuthClientConfig:

    """

    /**

     * API 요청에서 OAuth 클라이언트 설정을 검증해 만든다.

     */

    """

    cid = client_id.strip()

    secret = client_secret.strip()

    if not cid:

        raise ZendeskOAuthError("OAuth Client Identifier가 필요합니다.")

    if not secret:

        raise ZendeskOAuthError("OAuth Client Secret이 필요합니다.")

    return ZendeskOAuthClientConfig(

        client_id=cid,

        client_secret=secret,

        scopes=resolve_scopes(scopes),

    )





def config_from_instance(instance: Instance) -> ZendeskOAuthClientConfig:

    """DB에 저장된 인스턴스별 OAuth 설정을 읽는다."""

    return build_client_config(

        client_id=instance.oauth_client_id,

        client_secret=instance.oauth_client_secret,

        scopes=instance.oauth_scopes or None,

    )





def apply_client_config_to_instance(instance: Instance, config: ZendeskOAuthClientConfig) -> None:

    """인스턴스 행에 OAuth 클라이언트 설정을 반영한다."""

    instance.oauth_client_id = config.client_id

    instance.oauth_client_secret = config.client_secret

    instance.oauth_scopes = config.scopes


