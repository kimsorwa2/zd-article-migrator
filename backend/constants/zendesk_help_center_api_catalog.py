from __future__ import annotations

from typing import Any

from constants.zendesk_api_catalog_types import ZendeskApiOperation


DOC_BASE = "https://developer.zendesk.com/api-reference/help_center/help-center-api"
PRODUCT_DOC_URL = "https://developer.zendesk.com/api-reference/help_center/help-center-api/introduction/"


def _article_create_body() -> dict[str, Any]:
    return {
        "article": {
            "title": "Sample article",
            "locale": "en-us",
            "user_segment_id": None,
            "permission_group_id": 1,
            "body": "<p>Created via API Request console.</p>",
        }
    }


HELP_CENTER_API_OPERATIONS: tuple[ZendeskApiOperation, ...] = (
    # --- Help Center / Articles ---
    ZendeskApiOperation(
        id="hc.articles.list",
        category="Help Center",
        group="Articles",
        label="List Articles",
        method="GET",
        path_template="/api/v2/help_center/articles.json",
        doc_url=f"{DOC_BASE}/articles/#list-articles",
        default_query={"page[size]": "30"},
    ),
    ZendeskApiOperation(
        id="hc.articles.show",
        category="Help Center",
        group="Articles",
        label="Show Article",
        method="GET",
        path_template="/api/v2/help_center/articles/{article_id}.json",
        path_params=("article_id",),
        doc_url=f"{DOC_BASE}/articles/#show-article",
    ),
    ZendeskApiOperation(
        id="hc.articles.create",
        category="Help Center",
        group="Articles",
        label="Create Article",
        method="POST",
        path_template="/api/v2/help_center/{locale}/articles.json",
        path_params=("locale",),
        doc_url=f"{DOC_BASE}/articles/#create-article",
        sample_body=_article_create_body(),
    ),
    ZendeskApiOperation(
        id="hc.articles.update",
        category="Help Center",
        group="Articles",
        label="Update Article",
        method="PUT",
        path_template="/api/v2/help_center/articles/{article_id}.json",
        path_params=("article_id",),
        doc_url=f"{DOC_BASE}/articles/#update-article",
        sample_body={"article": {"title": "Updated title"}},
    ),
    ZendeskApiOperation(
        id="hc.articles.delete",
        category="Help Center",
        group="Articles",
        label="Delete Article",
        method="DELETE",
        path_template="/api/v2/help_center/articles/{article_id}.json",
        path_params=("article_id",),
        doc_url=f"{DOC_BASE}/articles/#delete-article",
    ),
    # --- Help Center / Categories ---
    ZendeskApiOperation(
        id="hc.categories.list",
        category="Help Center",
        group="Categories",
        label="List Categories",
        method="GET",
        path_template="/api/v2/help_center/categories.json",
        doc_url=f"{DOC_BASE}/categories/#list-categories",
    ),
    ZendeskApiOperation(
        id="hc.categories.show",
        category="Help Center",
        group="Categories",
        label="Show Category",
        method="GET",
        path_template="/api/v2/help_center/categories/{category_id}.json",
        path_params=("category_id",),
        doc_url=f"{DOC_BASE}/categories/#show-category",
    ),
    # --- Help Center / Sections ---
    ZendeskApiOperation(
        id="hc.sections.list",
        category="Help Center",
        group="Sections",
        label="List Sections",
        method="GET",
        path_template="/api/v2/help_center/sections.json",
        doc_url=f"{DOC_BASE}/sections/#list-sections",
    ),
    ZendeskApiOperation(
        id="hc.sections.show",
        category="Help Center",
        group="Sections",
        label="Show Section",
        method="GET",
        path_template="/api/v2/help_center/sections/{section_id}.json",
        path_params=("section_id",),
        doc_url=f"{DOC_BASE}/sections/#show-section",
    ),
    # --- Help Center / Locales ---
    ZendeskApiOperation(
        id="hc.locales.list",
        category="Help Center",
        group="Locales",
        label="List Help Center Locales",
        method="GET",
        path_template="/api/v2/help_center/locales.json",
        doc_url=f"{DOC_BASE}/locales/#list-help-center-locales",
    ),
    # --- Help Center / Translations ---
    ZendeskApiOperation(
        id="hc.translations.list",
        category="Help Center",
        group="Translations",
        label="List Article Translations",
        method="GET",
        path_template="/api/v2/help_center/articles/{article_id}/translations.json",
        path_params=("article_id",),
        doc_url=f"{DOC_BASE}/article_translations/#list-article-translations",
    ),
    # --- Help Center / User Segments ---
    ZendeskApiOperation(
        id="hc.user_segments.list",
        category="Help Center",
        group="User Segments",
        label="List User Segments",
        method="GET",
        path_template="/api/v2/help_center/user_segments.json",
        doc_url=f"{DOC_BASE}/user_segments/#list-user-segments",
    ),
)
