"""Optional free-data backtesting helpers for IPO Pulse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import math
import pandas as pd

BASELINE_COLUMNS = [
    "ipo_name",
    "listing_date",
    "issue_price",
    "pre_listing_gmp_percent",
    "actual_listing_price",
    "nifty_return_percent",
    "source_url",
]
REQUIRED_COLUMNS = ["ipo_name", "pre_listing_gmp_percent", "actual_listing_price"]


def default_baseline_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "ipo_backtesting_baseline.csv"


@dataclass(frozen=True)
class BaselineMetrics:
    samples: int
    direction_hit_rate: float | None
    gmp_return_correlation: float | None
    mean_actual_return: float | None
    mean_alpha_vs_nifty: float | None


def load_baseline_csv(path: Path | None = None) -> pd.DataFrame:
    """Load an optional historical baseline CSV without failing when it is absent."""
    path = default_baseline_path() if path is None else Path(path)
    if not path.exists():
        return pd.DataFrame(columns=BASELINE_COLUMNS)

    frame = pd.read_csv(path, comment="#")
    for column in BASELINE_COLUMNS:
        if column not in frame:
            frame[column] = None

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing and not frame.empty:
        raise ValueError(f"Baseline CSV is missing required column(s): {', '.join(missing)}")

    frame = frame[BASELINE_COLUMNS].copy()
    frame["listing_date"] = pd.to_datetime(frame["listing_date"], errors="coerce")
    frame["issue_price"] = pd.to_numeric(frame["issue_price"], errors="coerce")
    frame["pre_listing_gmp_percent"] = pd.to_numeric(frame["pre_listing_gmp_percent"], errors="coerce")
    frame["actual_listing_price"] = pd.to_numeric(frame["actual_listing_price"], errors="coerce")
    frame["nifty_return_percent"] = pd.to_numeric(frame["nifty_return_percent"], errors="coerce")

    price_basis = frame["issue_price"].where(frame["issue_price"].notna() & (frame["issue_price"] > 0), frame["actual_listing_price"])
    frame["actual_listing_return_percent"] = (frame["actual_listing_price"] - price_basis) / price_basis * 100
    return frame


def calculate_baseline_metrics(frame: pd.DataFrame) -> BaselineMetrics:
    if frame.empty or "actual_listing_return_percent" not in frame:
        return BaselineMetrics(0, None, None, None, None)

    valid = frame.dropna(subset=["pre_listing_gmp_percent", "actual_listing_return_percent"])
    if valid.empty:
        return BaselineMetrics(len(frame), None, None, None, None)

    direction_hits = (
        (valid["pre_listing_gmp_percent"] > 0) == (valid["actual_listing_return_percent"] > 0)
    ).sum()
    direction_hit_rate = float(direction_hits / len(valid) * 100)

    if len(valid) < 2:
        correlation = None
    else:
        correlation = float(valid["pre_listing_gmp_percent"].corr(valid["actual_listing_return_percent"]))
        if math.isnan(correlation):
            correlation = None

    alpha = valid["actual_listing_return_percent"]
    if "nifty_return_percent" in valid and valid["nifty_return_percent"].notna().any():
        alpha = alpha - valid["nifty_return_percent"]
    mean_alpha = float(alpha.mean()) if not alpha.empty else None
    mean_actual_return = float(valid["actual_listing_return_percent"].mean()) if not valid.empty else None

    return BaselineMetrics(
        samples=int(len(valid)),
        direction_hit_rate=direction_hit_rate,
        gmp_return_correlation=correlation,
        mean_actual_return=mean_actual_return,
        mean_alpha_vs_nifty=mean_alpha,
    )
