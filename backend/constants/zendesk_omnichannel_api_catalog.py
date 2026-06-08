from __future__ import annotations

from typing import Any

from constants.zendesk_api_catalog_types import ZendeskApiOperation


DOC_BASE = "https://developer.zendesk.com/api-reference/agent-availability"
PRODUCT_DOC_URL = "https://developer.zendesk.com/api-reference/agent-availability/introduction/"


def _agent_status_update_body() -> dict[str, Any]:
    return {
        "data": {
            "type": "agent_status",
            "attributes": {
                "agent_status_id": "1",
            },
        }
    }


OMNICHANNEL_API_OPERATIONS: tuple[ZendeskApiOperation, ...] = (
    # --- Agent Availability / Agent Availabilities ---
    ZendeskApiOperation(
        id="omni.agent_availabilities.list",
        category="Agent Availability",
        group="Agent Availabilities",
        label="List Agent Availabilities",
        method="GET",
        path_template="/api/v2/agent_availabilities.json",
        doc_url=f"{DOC_BASE}/agent-availability-api/agent_availabilities/#list-agent-availabilities",
        default_query={"page[size]": "25"},
    ),
    ZendeskApiOperation(
        id="omni.agent_availabilities.show",
        category="Agent Availability",
        group="Agent Availabilities",
        label="Show Agent Availability",
        method="GET",
        path_template="/api/v2/agent_availabilities/{agent_id}.json",
        path_params=("agent_id",),
        doc_url=f"{DOC_BASE}/agent-availability-api/agent_availabilities/#show-agent-availability",
    ),
    # --- Agent Availability / Unified Agent Statuses ---
    ZendeskApiOperation(
        id="omni.agent_statuses.list",
        category="Agent Availability",
        group="Unified Agent Statuses",
        label="List Unified Agent Statuses",
        method="GET",
        path_template="/api/v2/agent_availabilities/agent_statuses.json",
        doc_url=f"{DOC_BASE}/unified-agent-status-api/unified_agent_statuses/#list-unified-agent-statuses",
    ),
    ZendeskApiOperation(
        id="omni.agent_statuses.me",
        category="Agent Availability",
        group="Unified Agent Statuses",
        label="List My Unified Agent Statuses",
        method="GET",
        path_template="/api/v2/agent_availabilities/agent_statuses/me.json",
        doc_url=f"{DOC_BASE}/unified-agent-status-api/unified_agent_statuses/#list-my-unified-agent-statuses",
    ),
    ZendeskApiOperation(
        id="omni.agent_statuses.update",
        category="Agent Availability",
        group="Unified Agent Statuses",
        label="Update Agent Unified Status",
        method="PUT",
        path_template="/api/v2/agent_availabilities/agent_statuses/agents/{agent_id}.json",
        path_params=("agent_id",),
        doc_url=f"{DOC_BASE}/unified-agent-status-api/unified_agent_statuses/#update-agent-unified-status",
        sample_body=_agent_status_update_body(),
    ),
    # --- Omnichannel Routing / Queues ---
    ZendeskApiOperation(
        id="omni.queues.list",
        category="Omnichannel Routing",
        group="Queues",
        label="List Queues",
        method="GET",
        path_template="/api/v2/queues.json",
        doc_url=f"{DOC_BASE}/omnichannel_routing_queues/omnichannel_routing_queues/#list-queues",
    ),
    ZendeskApiOperation(
        id="omni.queues.show",
        category="Omnichannel Routing",
        group="Queues",
        label="Show Queue",
        method="GET",
        path_template="/api/v2/queues/{queue_id}.json",
        path_params=("queue_id",),
        doc_url=f"{DOC_BASE}/omnichannel_routing_queues/omnichannel_routing_queues/#show-queue",
    ),
    ZendeskApiOperation(
        id="omni.queues.definitions",
        category="Omnichannel Routing",
        group="Queues",
        label="List Queue Definitions",
        method="GET",
        path_template="/api/v2/queues/definitions.json",
        doc_url=f"{DOC_BASE}/omnichannel_routing_queues/omnichannel_routing_queues/#list-queue-definitions",
    ),
    ZendeskApiOperation(
        id="omni.queues.create",
        category="Omnichannel Routing",
        group="Queues",
        label="Create Queue",
        method="POST",
        path_template="/api/v2/queues.json",
        doc_url=f"{DOC_BASE}/omnichannel_routing_queues/omnichannel_routing_queues/#create-queue",
        sample_body={
            "queue": {
                "name": "Sample queue",
                "description": "Created via API Request console.",
                "priority": 1,
            }
        },
    ),
)
