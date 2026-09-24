from scripts.inspect_ipo_guru import format_payload


def test_format_payload_exposes_readable_ipo_and_gmp_values():
    payload = {
        "success": True,
        "plan": "free",
        "count": 1,
        "data": [
            {
                "name": "Example IPO",
                "issue_price": "100",
                "price_band": "95-100",
                "status": "open",
                "type": "mainboard",
                "gmp": {
                    "price": "25",
                    "percentage": "25%",
                    "estimated_listing_price": 125,
                    "updated_at": "2026-09-25 10:00:00",
                },
            }
        ],
    }

    result = format_payload(payload)

    assert result["ipos"][0]["name"] == "Example IPO"
    assert result["ipos"][0]["issue_price"] == "100"
    assert result["ipos"][0]["gmp"] == "25"
    assert result["ipos"][0]["gmp_percent"] == "25%"
    assert result["ipos"][0]["estimated_listing_price"] == 125
    assert result["ipos"][0]["lot_size"] is None