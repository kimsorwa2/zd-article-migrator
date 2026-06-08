from __future__ import annotations

from typing import Any

from constants.zendesk_api_catalog_types import ZendeskApiOperation


DOC_BASE = "https://developer.zendesk.com/api-reference/voice/talk-partner-edition-api"
PRODUCT_DOC_URL = "https://developer.zendesk.com/api-reference/voice/talk-partner-edition-api/basics/"


def _tpe_ticket_create_body() -> dict[str, Any]:
    return {
        "display_to_agent": 123456789,
        "ticket": {
            "via_id": 45,
            "subject": "Inbound call",
            "description": "Inbound call from +821012345678",
            "voice_comment": {
                "from": "+821012345678",
                "to": "+821098765432",
                "call_duration": 60,
            },
        },
    }


VOICE_TPE_API_OPERATIONS: tuple[ZendeskApiOperation, ...] = (
    # --- Talk Partner Edition / Tickets ---
    ZendeskApiOperation(
        id="tpe.tickets.create",
        category="Talk Partner Edition",
        group="Tickets",
        label="Create Ticket or Voicemail",
        method="POST",
        path_template="/api/v2/channels/voice/tickets.json",
        doc_url=f"{DOC_BASE}/tickets/#create-ticket-or-voicemail-ticket",
        sample_body=_tpe_ticket_create_body(),
    ),
    # --- Talk Partner Edition / Display ---
    ZendeskApiOperation(
        id="tpe.display.ticket",
        category="Talk Partner Edition",
        group="Display",
        label="Display Ticket to Agent",
        method="POST",
        path_template="/api/v2/channels/voice/agents/{agent_id}/tickets/{ticket_id}/display.json",
        path_params=("agent_id", "ticket_id"),
        doc_url=f"{DOC_BASE}/display/#display-ticket-to-agent",
    ),
    ZendeskApiOperation(
        id="tpe.display.user",
        category="Talk Partner Edition",
        group="Display",
        label="Display User to Agent",
        method="POST",
        path_template="/api/v2/channels/voice/agents/{agent_id}/users/{user_id}/display.json",
        path_params=("agent_id", "user_id"),
        doc_url=f"{DOC_BASE}/display/#display-user-to-agent",
    ),
    # --- Talk Partner Edition / Calls ---
    ZendeskApiOperation(
        id="tpe.calls.create",
        category="Talk Partner Edition",
        group="Calls",
        label="Create Call",
        method="POST",
        path_template="/api/v2/channels/voice/calls.json",
        doc_url=f"{DOC_BASE}/calls/#create-call",
        sample_body={
            "call": {
                "app_id": "sample-app-id",
                "from": "+821012345678",
                "to": "+821098765432",
                "direction": "inbound",
            }
        },
    ),
    ZendeskApiOperation(
        id="tpe.calls.show",
        category="Talk Partner Edition",
        group="Calls",
        label="Show Call",
        method="GET",
        path_template="/api/v2/channels/voice/calls/{call_id}.json",
        path_params=("call_id",),
        doc_url=f"{DOC_BASE}/calls/#show-call",
    ),
    ZendeskApiOperation(
        id="tpe.calls.update",
        category="Talk Partner Edition",
        group="Calls",
        label="Update Call",
        method="PUT",
        path_template="/api/v2/channels/voice/calls/{call_id}.json",
        path_params=("call_id",),
        doc_url=f"{DOC_BASE}/calls/#update-call",
        sample_body={"call": {"completed_at": "2026-06-08T12:00:00Z"}},
    ),
)
