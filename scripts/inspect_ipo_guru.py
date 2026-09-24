"""Fetch IPO Guru data and print readable IPO records, never credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from app.providers.ipo_guru_client import IPOGuruClient


def format_ipo_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Select the IPO fields currently available from the GMP endpoint."""
    gmp = record.get("gmp")
    gmp_data = gmp if isinstance(gmp, Mapping) else {}

    return {
        "name": record.get("name"),
        "issue_price": record.get("issue_price"),
        "price_band": record.get("price_band"),
        "lot_size": record.get("lot_size"),
        "open_date": record.get("open_date"),
        "close_date": record.get("close_date"),
        "listing_date": record.get("listing_date"),
        "actual_listing_price": record.get("actual_listing_price"),
        "gmp": gmp_data.get("price"),
        "gmp_percent": gmp_data.get("percentage"),
        "estimated_listing_price": gmp_data.get("estimated_listing_price"),
        "gmp_updated_at": gmp_data.get("updated_at"),
        "status": record.get("status"),
        "type": record.get("type"),
        "slug": record.get("slug"),
    }


def format_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a readable summary of the API response."""
    records = payload.get("data", [])
    if not isinstance(records, list):
        records = []

    return {
        "success": payload.get("success"),
        "plan": payload.get("plan"),
        "count": payload.get("count", len(records)),
        "ipos": [format_ipo_record(record) for record in records if isinstance(record, Mapping)],
    }


def main() -> int:
    api_key = os.getenv("IPO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing IPO_API_KEY")

    payload = IPOGuruClient(api_key=api_key).fetch_gmp()
    if not isinstance(payload, Mapping):
        raise RuntimeError("IPO Guru returned an unexpected response format")
    print(json.dumps(format_payload(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())