from __future__ import annotations

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# libpq/psycopg2 전용 쿼리 파라미터 — asyncpg가 URL에서 읽으면 Windows에서 SSL 오류가 날 수 있다.
_ASYNCPG_UNSUPPORTED_QUERY_KEYS = frozenset(
    {"sslmode", "sslrootcert", "sslcert", "sslkey", "channel_binding"}
)

# Neon 등 클라우드 호스트는 TLS가 필수다.
_SSL_REQUIRED_HOST_SUFFIXES = (".neon.tech",)


def prepare_asyncpg_database(database_url: str) -> tuple[str, dict[str, object]]:
    """
    /**
     * asyncpg용 DATABASE_URL과 connect_args를 정규화한다.
     * Neon URL의 sslmode 등 libpq 전용 파라미터를 제거하고, 필요 시 SSL 컨텍스트를 붙인다.
     * @param {str} database_url - 환경변수 DATABASE_URL 원본
     * @returns {tuple[str, dict[str, object]]} (정제된 URL, create_async_engine connect_args)
     */
    """
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query, keep_blank_values=False)

    ssl_mode = (query.get("sslmode") or [""])[0].lower()
    requires_ssl = ssl_mode in {"require", "verify-ca", "verify-full"}

    for key in _ASYNCPG_UNSUPPORTED_QUERY_KEYS:
        query.pop(key, None)

    host = (parsed.hostname or "").lower()
    if any(host.endswith(suffix) for suffix in _SSL_REQUIRED_HOST_SUFFIXES):
        requires_ssl = True

    clean_query = urlencode({key: values[0] for key, values in query.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args: dict[str, object] = {
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    }
    if requires_ssl:
        connect_args["ssl"] = ssl.create_default_context()

    return clean_url, connect_args
