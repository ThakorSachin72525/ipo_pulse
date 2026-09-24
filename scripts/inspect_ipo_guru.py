"""Fetch IPO Guru data and print readable IPO records, never credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from app.providers.ipo_guru_client import IPOGuruClient, normalize_gmp_record


def format_ipo_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Select the IPO fields currently available from the GMP endpoint."""
    return normalize_gmp_record(record)


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