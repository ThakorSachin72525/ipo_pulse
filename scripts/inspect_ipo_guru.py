"""Fetch IPO Guru data and print only its response shape, never credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence

from app.providers.ipo_guru_client import IPOGuruClient


def describe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): describe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return {"type": "list", "count": len(value), "first": describe(value[0]) if value else None}
    return type(value).__name__


def main() -> int:
    api_key = os.getenv("IPO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing IPO_API_KEY")

    payload = IPOGuruClient(api_key=api_key).fetch_gmp()
    print(json.dumps(describe(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())