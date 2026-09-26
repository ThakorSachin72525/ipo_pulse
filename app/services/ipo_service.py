"""Service layer for IPO domain operations."""

from __future__ import annotations

from app.models.ipo_model import GMPObservation, IPO, ListingResult, PredictionRecord


class IPOService:
    """Provides IPO-related operations for the current foundation layer."""

    @staticmethod
    def create_prediction(ipo: IPO, gmp: GMPObservation) -> PredictionRecord:
        return PredictionRecord.from_gmp(ipo=ipo, gmp_observation=gmp)

    @staticmethod
    def latest_pre_listing_gmp(
        ipo: IPO,
        observations: list[GMPObservation],
    ) -> GMPObservation:
        if not observations:
            raise ValueError("At least one GMP observation is required")
        filtered = [
            obs
            for obs in observations
            if obs.ipo_id == ipo.id
            and (ipo.listing_date is None or obs.date < ipo.listing_date)
        ]
        if not filtered:
            raise ValueError("No GMP observations exist before the listing date")
        return max(filtered, key=lambda obs: obs.date)

    @staticmethod
    def evaluate_listing_result(ipo: IPO, prediction: PredictionRecord) -> ListingResult:
        return ListingResult.from_prediction(ipo=ipo, prediction=prediction)

    @staticmethod
    def build_sample_ipo() -> IPO:
        return IPO(
            id="sample-ipo",
            name="Sample IPO",
            issue_price=100.0,
            lot_size=100,
        )
