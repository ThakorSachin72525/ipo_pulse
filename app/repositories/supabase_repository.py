"""Supabase persistence for IPO metadata and GMP observations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.config import Settings


IPO_COLUMNS = (
    "ipo_name",
    "issue_price",
    "lot_size",
    "price_band",
    "ipo_type",
    "status",
    "open_date",
    "close_date",
    "allotment_date",
    "refund_date",
    "demat_date",
    "listing_date",
    "listing_price",
    "issue_size",
    "face_value",
    "minimum_investment",
    "subscription_total",
    "source",
    "source_updated_at",
)


def build_ipo_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Select API fields that match the `ipos` table."""
    payload = {column: record.get(column) for column in IPO_COLUMNS}
    payload["ipo_name"] = record.get("ipo_name", record.get("name"))
    payload["source"] = record.get("source", "ipo_guru")
    if not payload["ipo_name"]:
        raise ValueError("IPO name is required")
    return {key: value for key, value in payload.items() if value is not None}


def build_gmp_payload(
    ipo_id: str,
    observation_at: datetime,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Build a UTC GMP observation payload for idempotent insertion."""
    if observation_at.tzinfo is None or observation_at.utcoffset() is None:
        raise ValueError("observation_at must include a timezone")
    observed_utc = observation_at.astimezone(timezone.utc).isoformat()
    return {
        "ipo_id": ipo_id,
        "observation_at": observed_utc,
        "gmp": record.get("gmp"),
        "gmp_percent": record.get("gmp_percent"),
        "estimated_listing_price": record.get("estimated_listing_price"),
        "source": record.get("source", "ipo_guru"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


class SupabaseRepository:
    """Write IPO records and append-only GMP observations to Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "SupabaseRepository":
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        return cls(create_client(settings.supabase_url, settings.supabase_key))

    def find_ipo_id(self, ipo_name: str, source: str = "ipo_guru") -> str | None:
        response = (
            self._client.table("ipos")
            .select("ipo_id")
            .eq("ipo_name", ipo_name)
            .eq("source", source)
            .limit(1)
            .execute()
        )
        return response.data[0]["ipo_id"] if response.data else None

    def upsert_ipo(self, record: dict[str, Any]) -> str:
        payload = build_ipo_payload(record)
        existing_id = self.find_ipo_id(payload["ipo_name"], payload["source"])
        if existing_id:
            self._client.table("ipos").update(payload).eq("ipo_id", existing_id).execute()
            return existing_id

        response = self._client.table("ipos").insert(payload).execute()
        if not response.data:
            raise RuntimeError("Supabase did not return the inserted IPO")
        return response.data[0]["ipo_id"]

    def upsert_gmp_observation(
        self,
        ipo_id: str,
        observation_at: datetime,
        record: dict[str, Any],
    ) -> str:
        payload = build_gmp_payload(ipo_id, observation_at, record)
        response = (
            self._client.table("ipo_gmp_history")
            .upsert(payload, on_conflict="ipo_id,observation_at,source")
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the GMP observation")
        return response.data[0]["gmp_history_id"]

    def verify_schema(self) -> tuple[str, ...]:
        """Run read-only queries against the required tables."""
        tables = ("ipos", "ipo_gmp_history")
        for table in tables:
            self._client.table(table).select("*").limit(1).execute()
        return tables
