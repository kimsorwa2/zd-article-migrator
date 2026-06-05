from __future__ import annotations



import os





def default_oauth_scopes() -> str:

    """앱 공통 scope 기본값(인스턴스별 oauth_scopes가 비어 있으면 사용)."""

    return os.getenv("ZENDESK_OAUTH_SCOPES", "read write").strip()


