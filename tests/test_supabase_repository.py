from datetime import datetime, timezone

import pytest

from app.repositories.supabase_repository import build_gmp_payload, build_ipo_payload


def test_build_ipo_payload_does_not_use_external_id():
    payload = build_ipo_payload(
        {
            "id": "external-slug",
            "name": "Example IPO",
            "issue_price": 100.0,
            "source": "ipo_guru",
        }
    )

    assert payload == {
        "ipo_name": "Example IPO",
        "issue_price": 100.0,
        "source": "ipo_guru",
    }
    assert "id" not in payload


def test_build_gmp_payload_normalizes_timestamp_to_utc():
    payload = build_gmp_payload(
        "owned-uuid",
        datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc),
        {"gmp": 48.0, "gmp_percent": 24.0, "estimated_listing_price": 148.0},
    )

    assert payload["observation_at"] == "2026-09-25T14:00:00+00:00"
    assert payload["gmp"] == 48.0


def test_build_gmp_payload_rejects_local_timestamp():
    with pytest.raises(ValueError, match="timezone"):
        build_gmp_payload("owned-uuid", datetime(2026, 9, 25, 14, 0), {})