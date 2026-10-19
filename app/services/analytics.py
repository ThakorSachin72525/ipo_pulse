"""Pure analytics helpers for IPO Pulse dashboard calculations."""

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd
from pandas.api.types import is_numeric_dtype


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in frame or not is_numeric_dtype(frame[column]):
        return None
    return pd.to_numeric(frame[column], errors="coerce")


def compute_accuracy_metrics(results: pd.DataFrame) -> dict[str, float | int | None]:
    """Return transparent prediction-error metrics from listing results."""
    if results.empty:
        return {
            "samples": 0,
            "direction_hit_rate": None,
            "mae": None,
            "rmse": None,
            "mape": None,
            "mean_signed_error": None,
        }

    total = len(results)
    correct = (
        pd.to_numeric(results.get("direction_accuracy"), errors="coerce")
        .fillna(0)
        .astype(bool)
        .sum()
        if "direction_accuracy" in results
        else 0
    )
    direction_hit_rate = float(correct / total * 100) if total else None

    prediction_error = _numeric_series(results, "prediction_error")
    percentage_error = _numeric_series(results, "percentage_error")

    if prediction_error is None:
        mae = None
        rmse = None
        mean_signed_error = None
    else:
        squared = (prediction_error.dropna() ** 2)
        mae = float(prediction_error.dropna().abs().mean()) if not prediction_error.dropna().empty else None
        rmse = float(math.sqrt(squared.mean())) if not squared.empty else None
        mean_signed_error = float(prediction_error.dropna().mean()) if not prediction_error.dropna().empty else None

    if percentage_error is None or percentage_error.dropna().empty:
        mape = None
    else:
        mape = float(percentage_error.dropna().mean())

    return {
        "samples": total,
        "direction_hit_rate": direction_hit_rate,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "mean_signed_error": mean_signed_error,
    }


def summarize_gmp_history(gmp_history: pd.DataFrame) -> pd.DataFrame:
    """Describe each IPO's GMP path using available public snapshots."""
    if gmp_history.empty:
        columns = [
            "name",
            "first_observation_at",
            "last_observation_at",
            "observations",
            "min_gmp",
            "max_gmp",
            "median_gmp",
            "final_gmp",
            "gmp_volatility",
        ]
        return pd.DataFrame(columns=columns)

    frame = gmp_history.copy()
    if "observation_at" in frame:
        frame["observation_at"] = pd.to_datetime(frame["observation_at"], errors="coerce")
        frame = frame.sort_values("observation_at")

    rows = []
    group_column = "name" if "name" in frame else frame.index.name
    for name, group in frame.groupby(group_column, dropna=False):
        gmp = pd.to_numeric(group.get("gmp"), errors="coerce").dropna()
        rows.append(
            {
                "name": name,
                "first_observation_at": group["observation_at"].min() if "observation_at" in group else None,
                "last_observation_at": group["observation_at"].max() if "observation_at" in group else None,
                "observations": int(group["gmp"].count()) if "gmp" in group else len(group),
                "min_gmp": float(gmp.min()) if not gmp.empty else None,
                "max_gmp": float(gmp.max()) if not gmp.empty else None,
                "median_gmp": float(gmp.median()) if not gmp.empty else None,
                "final_gmp": float(group.iloc[-1]["gmp"]) if "gmp" in group and pd.notna(group.iloc[-1].get("gmp")) else None,
                "gmp_volatility": float(gmp.std(ddof=0)) if len(gmp) > 1 else 0.0,
            }
        )

    return pd.DataFrame(rows)


def add_gmp_context_to_results(
    results: pd.DataFrame,
    gmp_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Add final GMP and observation count to results when names line up."""
    if results.empty:
        return results.copy()
    enriched = results.copy()
    if gmp_summary.empty:
        return enriched
    context_columns = ["final_gmp", "observations"]
    present_columns = [column for column in context_columns if column in gmp_summary.columns]
    join_columns = ["name"] + present_columns
    enriched = enriched.merge(gmp_summary[join_columns], on="name", how="left", validate="many_to_one")
    return enriched


def gmp_bucket(value: float | None, buckets: Iterable[tuple[str, float, float]] | None = None) -> str:
    """Label a value into a GMP bucket."""
    default_buckets = [
        ("Negative / zero", -math.inf, 0.0),
        ("1% - 5%", 0.0, 5.0),
        ("5% - 10%", 5.0, 10.0),
        ("> 10%", 10.0, math.inf),
    ]
    selected = list(buckets or default_buckets)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "Unknown"
    for label, lower, upper in selected:
        if lower < value <= upper:
            return label
    if value <= -math.inf:
        return selected[0][0]
    return selected[-1][0]


def add_gmp_bucket_column(results: pd.DataFrame) -> pd.DataFrame:
    """Add bucket labels to enriched result data."""
    if results.empty:
        return results.copy()
    enriched = results.copy()
    if "final_gmp" in enriched:
        enriched["gmp_bucket"] = enriched["final_gmp"].map(lambda value: gmp_bucket(None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)))
    else:
        enriched["gmp_bucket"] = "Unknown"
    return enriched


def accuracy_by_bucket(results: pd.DataFrame) -> pd.DataFrame:
    """Consolidate direction accuracy by GMP bucket."""
    if results.empty or "gmp_bucket" not in results or "direction_accuracy" not in results:
        return pd.DataFrame(columns=["gmp_bucket", "samples", "direction_hit_rate"])
    rows = []
    for bucket, group in results.groupby("gmp_bucket", dropna=False):
        valid = pd.to_numeric(group["direction_accuracy"], errors="coerce")
        samples = len(group)
        hit_rate = (valid.astype(bool).sum() / samples * 100) if samples else 0.0
        rows.append({"gmp_bucket": bucket, "samples": samples, "direction_hit_rate": float(hit_rate)})
    return pd.DataFrame(rows)
