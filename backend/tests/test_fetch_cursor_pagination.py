from services.fetch_service import FetchService


def test_resolve_cursor_next_page_url_stops_when_has_more_false() -> None:
    payload = {
        "meta": {"has_more": False},
        "links": {"next": "https://example.zendesk.com/api/v2/help_center/articles.json?page%5Bafter%5D=abc"},
    }
    assert FetchService._resolve_cursor_next_page_url(payload) is None


def test_resolve_cursor_next_page_url_returns_links_next() -> None:
    next_url = "https://example.zendesk.com/api/v2/help_center/articles.json?page%5Bsize%5D=100&page%5Bafter%5D=abc"
    payload = {
        "meta": {"has_more": True, "after_cursor": "abc"},
        "links": {"next": next_url},
    }
    assert FetchService._resolve_cursor_next_page_url(payload) == next_url


def test_resolve_cursor_next_page_url_ignores_offset_next_page() -> None:
    """오프셋 next_page만 있고 links.next가 없으면 다음 페이지로 진행하지 않는다."""
    payload = {
        "next_page": "https://example.zendesk.com/api/v2/help_center/articles.json?page=2&per_page=100",
    }
    assert FetchService._resolve_cursor_next_page_url(payload) is None


def test_build_articles_cursor_start_url_uses_page_size_param() -> None:
    url = FetchService._build_articles_cursor_start_url("https://brand.zendesk.com/api/v2/help_center")
    assert "page%5Bsize%5D=100" in url or "page[size]=100" in url
    assert "per_page" not in url
    assert "page=1" not in url
