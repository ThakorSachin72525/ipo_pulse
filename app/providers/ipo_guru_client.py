"""Client for the documented IPO Guru developer API."""

from __future__ import annotations

from typing import Any

import requests


class IPOGuruAPIError(RuntimeError):
    """Raised when IPO Guru returns an unsuccessful response."""


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
