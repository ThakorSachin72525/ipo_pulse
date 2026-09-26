"""Client for the documented IPO Guru developer API."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import requests


class IPOGuruAPIError(RuntimeError):
    """Raised when IPO Guru returns an unsuccessful response."""


def parse_number(value: Any) -> float | None:
    """Convert a currency/percentage string to a number when possible."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def normalize_gmp_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize fields available from IPO Guru's GMP endpoint."""
    gmp = record.get("gmp")
    gmp_data = gmp if isinstance(gmp, Mapping) else {}
    return {
        "name": record.get("name"),
        "issue_price": parse_number(record.get("issue_price")),
        "price_band": record.get("price_band"),
        "lot_size": record.get("lot_size"),
        "open_date": record.get("open_date"),
        "close_date": record.get("close_date"),
        "listing_date": record.get("listing_date"),
        "actual_listing_price": parse_number(record.get("actual_listing_price")),
        "gmp": parse_number(gmp_data.get("price")),
        "gmp_percent": parse_number(gmp_data.get("percentage")),
        "estimated_listing_price": parse_number(gmp_data.get("estimated_listing_price")),
        "gmp_updated_at": gmp_data.get("updated_at"),
        "status": record.get("status"),
        "type": record.get("type"),
        "slug": record.get("slug"),
    }


def normalize_ipo_detail(payload: Any) -> dict[str, Any]:
    """Normalize the Basic-plan IPO detail response used for listing reconciliation."""
    if not isinstance(payload, Mapping):
        raise IPOGuruAPIError("IPO Guru returned an unexpected IPO detail format")
    record = payload.get("data", payload)
    if not isinstance(record, Mapping):
        raise IPOGuruAPIError("IPO Guru returned an unexpected IPO detail format")

    listing = record.get("listing")
    listing = listing if isinstance(listing, Mapping) else {}
    listing_price = record.get("actual_listing_price")
    if listing_price is None:
        listing_price = record.get("listing_price")
    if listing_price is None:
        listing_price = listing.get("actual_listing_price", listing.get("listing_price"))

    return {
        "name": record.get("name"),
        "slug": record.get("slug"),
        "issue_price": parse_number(record.get("issue_price")),
        "lot_size": record.get("lot_size"),
        "listing_date": record.get("listing_date", listing.get("listing_date")),
        "actual_listing_price": parse_number(listing_price),
        "status": record.get("status"),
    }


class IPOGuruClient:
    """Fetch IPO and GMP data from IPO Guru."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.ipoguru.in/api/v2",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("IPO Guru API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_gmp(self, status: str = "open") -> Any:
        """Return the documented GMP endpoint payload without altering fields."""
        response = requests.get(
            f"{self._base_url}/gmp",
            headers={"X-API-KEY": self._api_key},
            params={"status": status},
            timeout=self._timeout,
        )
        if not response.ok:
            raise IPOGuruAPIError(
                f"IPO Guru request failed with HTTP {response.status_code}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise IPOGuruAPIError("IPO Guru returned invalid JSON") from error

    def fetch_ipo_detail(self, slug: str) -> Any:
        """Return the documented Basic-plan IPO detail endpoint payload."""
        if not slug:
            raise ValueError("IPO slug is required")
        response = requests.get(
            f"{self._base_url}/ipos/{slug}",
            headers={"X-API-KEY": self._api_key},
            timeout=self._timeout,
        )
        if not response.ok:
            raise IPOGuruAPIError(
                f"IPO Guru detail request failed with HTTP {response.status_code}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise IPOGuruAPIError("IPO Guru returned invalid IPO detail JSON") from error
