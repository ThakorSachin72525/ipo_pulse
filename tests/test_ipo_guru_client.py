import pytest

from app.providers.ipo_guru_client import IPOGuruClient, normalize_gmp_record, parse_number


def test_client_requires_api_key():
    with pytest.raises(ValueError, match="API key is required"):
        IPOGuruClient(api_key="")


def test_client_uses_documented_endpoint_and_header():
    client = IPOGuruClient(api_key="test-key")

    assert client._base_url == "https://www.ipoguru.in/api/v2"
    assert client._api_key == "test-key"


def test_gmp_record_normalizes_numeric_api_values():
    record = normalize_gmp_record(
        {
            "name": "Example IPO",
            "issue_price": "₹ 100",
            "gmp": {"price": "25", "percentage": "25%", "estimated_listing_price": 125},
        }
    )

    assert parse_number("₹ 1,250.50") == 1250.50
    assert record["issue_price"] == 100.0
    assert record["gmp"] == 25.0
    assert record["gmp_percent"] == 25.0
    assert record["estimated_listing_price"] == 125.0