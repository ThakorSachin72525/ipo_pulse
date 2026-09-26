"""Insert an idempotent, clearly marked Phase 5 sample IPO and outcome."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from app.config import Settings
from app.models.ipo_model import GMPObservation, IPO
from app.repositories.supabase_repository import SupabaseRepository
from app.services.ipo_service import IPOService


SAMPLE_NAME = "IPO Pulse Phase 5 Sample"
SAMPLE_SOURCE = "ipo_pulse_phase5_sample"
GMP_DATE = date(2025, 1, 14)
LISTING_DATE = date(2025, 1, 15)


def main() -> int:
    repository = SupabaseRepository.from_settings(Settings.from_env())
    actual_listing_price = 112.0
    ipo_record = {
        "name": SAMPLE_NAME,
        "issue_price": 100.0,
        "lot_size": 20,
        "listing_date": LISTING_DATE.isoformat(),
        "actual_listing_price": actual_listing_price,
        "status": "sample",
        "source": SAMPLE_SOURCE,
    }
    ipo_id = repository.upsert_ipo(ipo_record)
    ipo = IPO(
        id=ipo_id,
        name=SAMPLE_NAME,
        issue_price=100.0,
        lot_size=20,
        listing_date=LISTING_DATE,
        actual_listing_price=actual_listing_price,
    )
    gmp = GMPObservation(
        ipo_id=ipo_id,
        date=GMP_DATE,
        gmp=15.0,
        gmp_percent=15.0,
        source=SAMPLE_SOURCE,
    )
    observation_at = datetime.combine(GMP_DATE, time.min, tzinfo=timezone.utc)
    gmp_history_id = repository.upsert_gmp_observation(
        ipo_id,
        observation_at,
        {
            "gmp": gmp.gmp,
            "gmp_percent": gmp.gmp_percent,
            "estimated_listing_price": ipo.issue_price + gmp.gmp,
            "source": SAMPLE_SOURCE,
        },
    )
    prediction = IPOService.create_prediction(ipo, gmp)
    prediction_id = repository.upsert_prediction(ipo_id, gmp_history_id, ipo, gmp)
    result_id = repository.upsert_listing_result(ipo_id, prediction_id, ipo, prediction)

    print(f"Sample IPO: {SAMPLE_NAME}")
    print(f"Expected listing price: {prediction.expected_listing_price:.2f}")
    print(f"Actual listing price: {actual_listing_price:.2f}")
    print(f"Listing-result record: {result_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
