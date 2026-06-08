"""Zendesk API 통합 카탈로그 단위 테스트."""

from constants.zendesk_api_catalog import build_zendesk_api_catalog


def test_build_zendesk_api_catalog_includes_all_products() -> None:
    products = build_zendesk_api_catalog()
    product_ids = [product.id for product in products]
    assert product_ids == ["ticketing", "help-center", "voice-tpe", "custom-data", "omnichannel"]


def test_build_zendesk_api_catalog_has_operations() -> None:
    products = build_zendesk_api_catalog()
    operation_counts = [
        sum(len(group.operations) for category in product.categories for group in category.groups)
        for product in products
    ]
    assert all(count > 0 for count in operation_counts)
