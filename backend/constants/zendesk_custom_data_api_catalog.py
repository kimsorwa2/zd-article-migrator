from __future__ import annotations

from typing import Any

from constants.zendesk_api_catalog_types import ZendeskApiOperation


DOC_BASE = "https://developer.zendesk.com/api-reference/custom-data/custom-objects"
PRODUCT_DOC_URL = "https://developer.zendesk.com/api-reference/custom-data/custom-objects/introduction/"


def _custom_object_create_body() -> dict[str, Any]:
    return {
        "custom_object": {
            "key": "sample_object",
            "title": "Sample Object",
            "title_pluralized": "Sample Objects",
        }
    }


def _custom_object_record_create_body() -> dict[str, Any]:
    return {
        "custom_object_record": {
            "name": "Sample record",
            "custom_object_fields": {},
        }
    }


CUSTOM_DATA_API_OPERATIONS: tuple[ZendeskApiOperation, ...] = (
    # --- Custom Objects / Custom Objects ---
    ZendeskApiOperation(
        id="cd.objects.list",
        category="Custom Objects",
        group="Custom Objects",
        label="List Custom Objects",
        method="GET",
        path_template="/api/v2/custom_objects.json",
        doc_url=f"{DOC_BASE}/custom_objects/#list-custom-objects",
    ),
    ZendeskApiOperation(
        id="cd.objects.show",
        category="Custom Objects",
        group="Custom Objects",
        label="Show Custom Object",
        method="GET",
        path_template="/api/v2/custom_objects/{custom_object_key}.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_objects/#show-custom-object",
    ),
    ZendeskApiOperation(
        id="cd.objects.create",
        category="Custom Objects",
        group="Custom Objects",
        label="Create Custom Object",
        method="POST",
        path_template="/api/v2/custom_objects.json",
        doc_url=f"{DOC_BASE}/custom_objects/#create-custom-object",
        sample_body=_custom_object_create_body(),
    ),
    # --- Custom Objects / Custom Object Fields ---
    ZendeskApiOperation(
        id="cd.fields.list",
        category="Custom Objects",
        group="Custom Object Fields",
        label="List Custom Object Fields",
        method="GET",
        path_template="/api/v2/custom_objects/{custom_object_key}/fields.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_object_fields/#list-custom-object-fields",
    ),
    ZendeskApiOperation(
        id="cd.fields.create",
        category="Custom Objects",
        group="Custom Object Fields",
        label="Create Custom Object Field",
        method="POST",
        path_template="/api/v2/custom_objects/{custom_object_key}/fields.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_object_fields/#create-custom-object-field",
        sample_body={
            "custom_object_field": {
                "key": "sample_field",
                "title": "Sample Field",
                "type": "text",
            }
        },
    ),
    # --- Custom Objects / Custom Object Records ---
    ZendeskApiOperation(
        id="cd.records.list",
        category="Custom Objects",
        group="Custom Object Records",
        label="List Custom Object Records",
        method="GET",
        path_template="/api/v2/custom_objects/{custom_object_key}/records.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_object_records/#list-custom-object-records",
        default_query={"page[size]": "25"},
    ),
    ZendeskApiOperation(
        id="cd.records.show",
        category="Custom Objects",
        group="Custom Object Records",
        label="Show Custom Object Record",
        method="GET",
        path_template="/api/v2/custom_objects/{custom_object_key}/records/{custom_object_record_id}.json",
        path_params=("custom_object_key", "custom_object_record_id"),
        doc_url=f"{DOC_BASE}/custom_object_records/#show-custom-object-record",
    ),
    ZendeskApiOperation(
        id="cd.records.create",
        category="Custom Objects",
        group="Custom Object Records",
        label="Create Custom Object Record",
        method="POST",
        path_template="/api/v2/custom_objects/{custom_object_key}/records.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_object_records/#create-custom-object-record",
        sample_body=_custom_object_record_create_body(),
    ),
    ZendeskApiOperation(
        id="cd.records.search",
        category="Custom Objects",
        group="Custom Object Records",
        label="Search Custom Object Records",
        method="POST",
        path_template="/api/v2/custom_objects/{custom_object_key}/records/search.json",
        path_params=("custom_object_key",),
        doc_url=f"{DOC_BASE}/custom_object_records/#search-custom-object-records",
        default_query={"query": "*"},
        sample_body={"filter": {"$and": [{"name": {"$contains": "sample"}}]}},
    ),
)
