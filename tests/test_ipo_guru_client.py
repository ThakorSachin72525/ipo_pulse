import pytest

from app.providers.ipo_guru_client import (
    IPOGuruClient,
    normalize_gmp_record,
    normalize_ipo_detail,
    parse_number,
)


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


def test_client_fetches_documented_ipo_detail_endpoint(monkeypatch):
    requested = []
    payload = {"data": {"name": "Example IPO", "actual_listing_price": "125"}}

    class Response:
        ok = True

        def json(self):
            return payload

    def fake_get(url, headers, timeout):
        requested.append((url, headers, timeout))
        return Response()

    monkeypatch.setattr("app.providers.ipo_guru_client.requests.get", fake_get)

    result = IPOGuruClient("test-key").fetch_ipo_detail("example-ipo")

    assert result == payload
    assert requested[0][0] == "https://www.ipoguru.in/api/v2/ipos/example-ipo"
    assert requested[0][1] == {"X-API-KEY": "test-key"}


def test_normalize_ipo_detail_extracts_documented_actual_listing_price():
    record = normalize_ipo_detail(
        {
            "data": {
                "name": "Example IPO",
                "slug": "example-ipo",
                "issue_price": "100",
                "lot_size": 20,
                "listing_date": "2026-09-25",
                "actual_listing_price": "125.50",
            }
        }
    )

    assert record["name"] == "Example IPO"
    assert record["slug"] == "example-ipo"
    assert record["actual_listing_price"] == 125.5
    assert record["listing_date"] == "2026-09-25"


def test_normalize_ipo_detail_reads_listing_price_from_listing_object():
    record = normalize_ipo_detail(
        {
            "data": {
                "name": "Example IPO",
                "listing": {"listing_date": "2026-09-25", "listing_price": "125"},
            }
        }
    )

    assert record["listing_date"] == "2026-09-25"
    assert record["actual_listing_price"] == 125.0