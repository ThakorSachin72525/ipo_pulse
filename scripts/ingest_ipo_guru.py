"""Fetch IPO Guru data and persist IPO metadata plus GMP-backed predictions."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from collections.abc import Mapping
from typing import Any

from app.config import Settings
from app.models.ipo_model import GMPObservation, IPO
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


def parse_optional_iso_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def main() -> int:
    settings = Settings.from_env()
    if not settings.ipo_api_key:
        raise RuntimeError("Missing IPO_API_KEY")

    client = IPOGuruClient(api_key=settings.ipo_api_key)
    repository = SupabaseRepository.from_settings(settings)
    records = extract_records(client.fetch_gmp())
    ipo_count = 0
    gmp_count = 0
    prediction_count = 0

    for raw_record in records:
        record = normalize_gmp_record(raw_record)
        observation_at = parse_observation_at(record.get("gmp_updated_at"))
        record["source"] = "ipo_guru"
        record["source_updated_at"] = observation_at.isoformat()
        ipo_id = repository.upsert_ipo(record)
        ipo_count += 1

        if record["gmp"] is not None:
            gmp_history_id = repository.upsert_gmp_observation(ipo_id, observation_at, record)
            gmp_count += 1

            gmp = GMPObservation(
                ipo_id=ipo_id,
                date=observation_at.date(),
                gmp=float(record["gmp"]),
                gmp_percent=float(record["gmp_percent"] or 0.0),
                source="ipo_guru",
                fetched_at=observation_at.date(),
            )
            issue_price = record.get("issue_price")
            listing_date = parse_optional_iso_date(record.get("listing_date"))
            is_pre_listing = listing_date is None or gmp.date < listing_date
            if issue_price is not None and issue_price > 0 and is_pre_listing:
                ipo = IPO(
                    id=ipo_id,
                    name=record.get("name") or "IPO",
                    issue_price=float(issue_price),
                    lot_size=int(record["lot_size"] or 1),
                    listing_date=listing_date,
                )
                repository.upsert_prediction(ipo_id, gmp_history_id, ipo, gmp)
                prediction_count += 1

    print(f"IPO records upserted: {ipo_count}")
    print(f"GMP observations upserted: {gmp_count}")
    print(f"Predictions upserted: {prediction_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())