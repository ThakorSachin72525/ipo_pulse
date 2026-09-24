"""Fetch IPO Guru data and persist IPO metadata plus current GMP snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections.abc import Mapping
from typing import Any

from app.config import Settings
from app.providers.ipo_guru_client import IPOGuruClient, normalize_gmp_record
from app.repositories.supabase_repository import SupabaseRepository


PROVIDER_TIMEZONE = ZoneInfo("Asia/Kolkata")


def parse_observation_at(value: Any) -> datetime:
    """Parse an IPO Guru timestamp and return an aware UTC datetime."""
    if not value:
        raise ValueError("IPO Guru GMP updated_at is required")
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"Unsupported IPO Guru timestamp: {value}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PROVIDER_TIMEZONE)
    return parsed.astimezone(timezone.utc)


def extract_records(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
        raise RuntimeError("IPO Guru returned an unexpected response format")
    return [record for record in payload["data"] if isinstance(record, Mapping)]


def main() -> int:
    settings = Settings.from_env()
    if not settings.ipo_api_key:
        raise RuntimeError("Missing IPO_API_KEY")

    client = IPOGuruClient(api_key=settings.ipo_api_key)
    repository = SupabaseRepository.from_settings(settings)
    records = extract_records(client.fetch_gmp())
    ipo_count = 0
    gmp_count = 0

    for raw_record in records:
        record = normalize_gmp_record(raw_record)
        observation_at = parse_observation_at(record.get("gmp_updated_at"))
        record["source"] = "ipo_guru"
        record["source_updated_at"] = observation_at.isoformat()
        ipo_id = repository.upsert_ipo(record)
        ipo_count += 1
        if record["gmp"] is not None:
            repository.upsert_gmp_observation(ipo_id, observation_at, record)
            gmp_count += 1

    print(f"IPO records upserted: {ipo_count}")
    print(f"GMP observations upserted: {gmp_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())