"""Domain models for IPO tracking and prediction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(slots=True)
class IPO:
    """IPO metadata used across the tracking pipeline."""

    id: str
    name: str
    issue_price: float
    lot_size: int = 1
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    listing_date: Optional[date] = None
    actual_listing_price: Optional[float] = None

    @property
    def investment(self) -> float:
        return self.issue_price * self.lot_size


@dataclass(slots=True)
class GMPObservation:
    """Daily GMP observation snapshot for an IPO."""

    ipo_id: str
    date: date
    gmp: float
    gmp_percent: float
    source: str = "ipo_guru"
    fetched_at: Optional[date] = None


@dataclass(slots=True)
class PredictionRecord:
    """A GMP-based prediction stored before the IPO lists."""

    ipo_id: str
    gmp_date: date
    gmp_value: float
    gmp_percent: float
    issue_price: float
    lot_size: int
    expected_listing_price: float = field(init=False)
    expected_profit: float = field(init=False)
    expected_return: float = field(init=False)
    source: str = "ipo_guru"

    @classmethod
    def from_gmp(cls, ipo: IPO, gmp_observation: GMPObservation) -> "PredictionRecord":
        record = cls(
            ipo_id=ipo.id,
            gmp_date=gmp_observation.date,
            gmp_value=gmp_observation.gmp,
            gmp_percent=gmp_observation.gmp_percent,
            issue_price=ipo.issue_price,
            lot_size=ipo.lot_size,
            source=gmp_observation.source,
        )

        record.expected_listing_price = record.issue_price + record.gmp_value
        record.expected_profit = (record.expected_listing_price - record.issue_price) * record.lot_size
        record.expected_return = (
            (record.expected_profit / (record.issue_price * record.lot_size)) * 100
            if record.issue_price * record.lot_size
            else 0.0
        )
        return record


@dataclass(slots=True)
class ListingResult:
    """Outcome after a listed IPO has settled."""

    ipo_id: str
    actual_listing_price: float
    predicted_listing_price: float
    actual_gain_percent: float
    prediction_error: float
    percentage_error: float
    direction_accuracy: bool

    @classmethod
    def from_prediction(cls, ipo: IPO, prediction: PredictionRecord) -> "ListingResult":
        if ipo.actual_listing_price is None:
            raise ValueError("actual_listing_price is required to evaluate a prediction")

        actual_gain_percent = ((ipo.actual_listing_price - ipo.issue_price) / ipo.issue_price) * 100
        prediction_error = ipo.actual_listing_price - prediction.expected_listing_price
        percentage_error = (abs(prediction_error) / prediction.expected_listing_price) * 100
        direction_accuracy = (actual_gain_percent >= 0) == (prediction.expected_listing_price >= ipo.issue_price)

        return cls(
            ipo_id=ipo.id,
            actual_listing_price=ipo.actual_listing_price,
            predicted_listing_price=prediction.expected_listing_price,
            actual_gain_percent=actual_gain_percent,
            prediction_error=prediction_error,
            percentage_error=percentage_error,
            direction_accuracy=direction_accuracy,
        )
