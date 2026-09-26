"""Fetch actual listing prices and evaluate saved pre-listing predictions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import Settings
from app.models.ipo_model import IPO, PredictionRecord
from app.providers.ipo_guru_client import IPOGuruClient, normalize_ipo_detail, parse_number
from app.repositories.supabase_repository import SupabaseRepository


PROVIDER_TIMEZONE = ZoneInfo("Asia/Kolkata")


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def prediction_from_record(record: dict[str, Any]) -> PredictionRecord:
    gmp_date = parse_date(record.get("gmp_date"))
    if gmp_date is None:
        raise ValueError(f"Prediction {record.get('prediction_id')} has no valid GMP date")
    issue_price = record.get("issue_price")
    expected_listing_price = record.get("expected_listing_price")
    if issue_price is None or float(issue_price) <= 0:
        raise ValueError(f"Prediction {record.get('prediction_id')} has no positive issue price")
    if expected_listing_price is None:
        raise ValueError(f"Prediction {record.get('prediction_id')} has no expected listing price")
    prediction = PredictionRecord(
        ipo_id=record["ipo_id"],
        gmp_date=gmp_date,
        gmp_value=float(record["gmp_value"] or 0.0),
        gmp_percent=float(record["gmp_percent"] or 0.0),
        issue_price=float(issue_price),
        lot_size=int(record["lot_size"] or 1),
        source=record.get("source") or "ipo_guru",
    )
    prediction.expected_listing_price = float(expected_listing_price)
    prediction.expected_profit = float(record["expected_profit"] or 0.0)
    prediction.expected_return = float(record["expected_return"] or 0.0)
    return prediction


def reconcile_listings(client: IPOGuruClient, repository: SupabaseRepository) -> tuple[int, int]:
    ipo_count = 0
    result_count = 0
    today = datetime.now(PROVIDER_TIMEZONE).date()

    for candidate in repository.get_ipo_records_for_reconciliation():
        slug = candidate.get("ipo_slug")
        listing_date = parse_date(candidate.get("listing_date"))
        # Avoid spending detail requests on IPOs that have not listed yet,
        # or whose scheduled listing date is unavailable.
        if not slug or listing_date is None or listing_date > today:
            continue

        predictions = repository.get_predictions_for_ipo(candidate["ipo_id"])
        if not predictions:
            continue

        actual_listing_price = parse_number(candidate.get("listing_price"))
        if actual_listing_price is None or actual_listing_price <= 0:
            detail = normalize_ipo_detail(client.fetch_ipo_detail(slug))
            actual_listing_price = detail.get("actual_listing_price")
            listing_date = parse_date(detail.get("listing_date")) or listing_date
        if actual_listing_price is None or listing_date is None:
            continue

        repository.update_listing_data(
            candidate["ipo_id"],
            listing_date.isoformat(),
            actual_listing_price,
        )
        ipo_count += 1

        for prediction_record in predictions:
            prediction = prediction_from_record(prediction_record)
            if prediction.gmp_date >= listing_date:
                continue
            ipo = IPO(
                id=candidate["ipo_id"],
                name=candidate["ipo_name"],
                issue_price=prediction.issue_price,
                lot_size=prediction.lot_size,
                listing_date=listing_date,
                actual_listing_price=actual_listing_price,
            )
            repository.upsert_listing_result(
                candidate["ipo_id"],
                prediction_record["prediction_id"],
                ipo,
                prediction,
            )
            result_count += 1

    return ipo_count, result_count


def main() -> int:
    settings = Settings.from_env()
    if not settings.ipo_api_key:
        raise RuntimeError("Missing IPO_API_KEY")

    client = IPOGuruClient(api_key=settings.ipo_api_key)
    repository = SupabaseRepository.from_settings(settings)
    ipo_count, result_count = reconcile_listings(client, repository)
    print(f"Listed IPOs reconciled: {ipo_count}")
    print(f"Prediction outcomes stored: {result_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
