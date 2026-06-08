from __future__ import annotations

from typing import Any

from constants.zendesk_api_catalog_types import ZendeskApiOperation


DOC_BASE = "https://developer.zendesk.com/api-reference/ticketing"
PRODUCT_DOC_URL = "https://developer.zendesk.com/api-reference/ticketing/introduction/"


def _ticket_create_body() -> dict[str, Any]:
    return {
        "ticket": {
            "subject": "Sample ticket",
            "comment": {"body": "Created via API Request console."},
        }
    }


# Ticketing API 소개 문서 사이드바 구조 기준 시드 operation
TICKETING_API_OPERATIONS: tuple[ZendeskApiOperation, ...] = (
    # --- Tickets / Tickets ---
    ZendeskApiOperation(
        id="tickets.list",
        category="Tickets",
        group="Tickets",
        label="List Tickets",
        method="GET",
        path_template="/api/v2/tickets.json",
        doc_url=f"{DOC_BASE}/tickets/tickets/#list-tickets",
        default_query={"page[size]": "25"},
    ),
    ZendeskApiOperation(
        id="tickets.show",
        category="Tickets",
        group="Tickets",
        label="Show Ticket",
        method="GET",
        path_template="/api/v2/tickets/{ticket_id}.json",
        path_params=("ticket_id",),
        doc_url=f"{DOC_BASE}/tickets/tickets/#show-ticket",
    ),
    ZendeskApiOperation(
        id="tickets.create",
        category="Tickets",
        group="Tickets",
        label="Create Ticket",
        method="POST",
        path_template="/api/v2/tickets.json",
        doc_url=f"{DOC_BASE}/tickets/tickets/#create-ticket",
        sample_body=_ticket_create_body(),
    ),
    ZendeskApiOperation(
        id="tickets.update",
        category="Tickets",
        group="Tickets",
        label="Update Ticket",
        method="PUT",
        path_template="/api/v2/tickets/{ticket_id}.json",
        path_params=("ticket_id",),
        doc_url=f"{DOC_BASE}/tickets/tickets/#update-ticket",
        sample_body={"ticket": {"comment": {"body": "Updated via API Request console."}}},
    ),
    ZendeskApiOperation(
        id="tickets.delete",
        category="Tickets",
        group="Tickets",
        label="Delete Ticket",
        method="DELETE",
        path_template="/api/v2/tickets/{ticket_id}.json",
        path_params=("ticket_id",),
        doc_url=f"{DOC_BASE}/tickets/tickets/#delete-ticket",
    ),
    # --- Tickets / Ticket Comments ---
    ZendeskApiOperation(
        id="ticket_comments.list",
        category="Tickets",
        group="Ticket Comments",
        label="List Comments",
        method="GET",
        path_template="/api/v2/tickets/{ticket_id}/comments.json",
        path_params=("ticket_id",),
        doc_url=f"{DOC_BASE}/tickets/ticket_comments/#list-comments",
    ),
    # --- Users / Users ---
    ZendeskApiOperation(
        id="users.me",
        category="Users",
        group="Users",
        label="Show Self",
        method="GET",
        path_template="/api/v2/users/me.json",
        doc_url=f"{DOC_BASE}/users/users/#show-self",
    ),
    ZendeskApiOperation(
        id="users.list",
        category="Users",
        group="Users",
        label="List Users",
        method="GET",
        path_template="/api/v2/users.json",
        doc_url=f"{DOC_BASE}/users/users/#list-users",
        default_query={"page[size]": "25"},
    ),
    ZendeskApiOperation(
        id="users.show",
        category="Users",
        group="Users",
        label="Show User",
        method="GET",
        path_template="/api/v2/users/{user_id}.json",
        path_params=("user_id",),
        doc_url=f"{DOC_BASE}/users/users/#show-user",
    ),
    ZendeskApiOperation(
        id="users.create",
        category="Users",
        group="Users",
        label="Create User",
        method="POST",
        path_template="/api/v2/users.json",
        doc_url=f"{DOC_BASE}/users/users/#create-user",
        sample_body={"user": {"name": "Sample User", "email": "sample@example.com", "role": "end-user"}},
    ),
    # --- Organizations / Organizations ---
    ZendeskApiOperation(
        id="organizations.list",
        category="Organizations",
        group="Organizations",
        label="List Organizations",
        method="GET",
        path_template="/api/v2/organizations.json",
        doc_url=f"{DOC_BASE}/organizations/organizations/#list-organizations",
        default_query={"page[size]": "25"},
    ),
    ZendeskApiOperation(
        id="organizations.show",
        category="Organizations",
        group="Organizations",
        label="Show Organization",
        method="GET",
        path_template="/api/v2/organizations/{organization_id}.json",
        path_params=("organization_id",),
        doc_url=f"{DOC_BASE}/organizations/organizations/#show-organization",
    ),
    # --- Groups / Groups ---
    ZendeskApiOperation(
        id="groups.list",
        category="Groups",
        group="Groups",
        label="List Groups",
        method="GET",
        path_template="/api/v2/groups.json",
        doc_url=f"{DOC_BASE}/groups/groups/#list-groups",
    ),
    ZendeskApiOperation(
        id="groups.show",
        category="Groups",
        group="Groups",
        label="Show Group",
        method="GET",
        path_template="/api/v2/groups/{group_id}.json",
        path_params=("group_id",),
        doc_url=f"{DOC_BASE}/groups/groups/#show-group",
    ),
    # --- Ticket Management / Search ---
    ZendeskApiOperation(
        id="search.query",
        category="Ticket Management",
        group="Search",
        label="Search",
        method="GET",
        path_template="/api/v2/search.json",
        doc_url=f"{DOC_BASE}/ticket-management/search/#search",
        default_query={"query": "type:ticket status:open"},
    ),
    ZendeskApiOperation(
        id="tags.list",
        category="Ticket Management",
        group="Tags",
        label="List Tags",
        method="GET",
        path_template="/api/v2/tags.json",
        doc_url=f"{DOC_BASE}/ticket-management/tags/#list-tags",
    ),
    # --- Business Rules / Views ---
    ZendeskApiOperation(
        id="views.list",
        category="Business Rules",
        group="Views",
        label="List Views",
        method="GET",
        path_template="/api/v2/views.json",
        doc_url=f"{DOC_BASE}/business-rules/views/#list-views",
    ),
    ZendeskApiOperation(
        id="macros.list",
        category="Business Rules",
        group="Macros",
        label="List Macros",
        method="GET",
        path_template="/api/v2/macros.json",
        doc_url=f"{DOC_BASE}/business-rules/macros/#list-macros",
    ),
    ZendeskApiOperation(
        id="triggers.list",
        category="Business Rules",
        group="Ticket Triggers",
        label="List Triggers",
        method="GET",
        path_template="/api/v2/triggers.json",
        doc_url=f"{DOC_BASE}/business-rules/ticket_triggers/#list-triggers",
    ),
    # --- Account Configuration / Brands ---
    ZendeskApiOperation(
        id="brands.list",
        category="Account Configuration",
        group="Brands",
        label="List Brands",
        method="GET",
        path_template="/api/v2/brands.json",
        doc_url=f"{DOC_BASE}/account-configuration/brands/#list-brands",
    ),
    ZendeskApiOperation(
        id="brands.show",
        category="Account Configuration",
        group="Brands",
        label="Show Brand",
        method="GET",
        path_template="/api/v2/brands/{brand_id}.json",
        path_params=("brand_id",),
        doc_url=f"{DOC_BASE}/account-configuration/brands/#show-brand",
    ),
    ZendeskApiOperation(
        id="locales.list",
        category="Account Configuration",
        group="Locales",
        label="List Locales",
        method="GET",
        path_template="/api/v2/locales.json",
        doc_url=f"{DOC_BASE}/account-configuration/locales/#list-locales",
    ),
    # --- OAuth / OAuth Tokens ---
    ZendeskApiOperation(
        id="oauth_tokens.list",
        category="OAuth",
        group="OAuth Tokens",
        label="List Tokens",
        method="GET",
        path_template="/api/v2/oauth/tokens.json",
        doc_url=f"{DOC_BASE}/oauth/oauth_tokens/#list-tokens",
    ),
)
