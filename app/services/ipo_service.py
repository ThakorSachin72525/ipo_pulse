"""Service layer for IPO domain operations."""

from __future__ import annotations

from app.models.ipo_model import GMPObservation, IPO, PredictionRecord


class IPOService:
    """Provides IPO-related operations for the current foundation layer."""

    @staticmethod
    def create_prediction(ipo: IPO, gmp: GMPObservation) -> PredictionRecord:
        return PredictionRecord.from_gmp(ipo=ipo, gmp_observation=gmp)

    @staticmethod
    def build_sample_ipo() -> IPO:
        return IPO(
            id="sample-ipo",
            name="Sample IPO",
            issue_price=100.0,
            lot_size=100,
        )
