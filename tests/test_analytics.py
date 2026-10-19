from datetime import datetime

import pandas as pd

from app.services.analytics import (
    accuracy_by_bucket,
    add_gmp_bucket_column,
    add_gmp_context_to_results,
    compute_accuracy_metrics,
    summarize_gmp_history,
)


def test_compute_accuracy_metrics_matches_known_values():
    results = pd.DataFrame(
        [
            {"direction_accuracy": True, "prediction_error": 2.0, "percentage_error": 2.0},
            {"direction_accuracy": False, "prediction_error": -4.0, "percentage_error": 4.0},
        ]
    )

    metrics = compute_accuracy_metrics(results)
    assert metrics["samples"] == 2
    assert metrics["direction_hit_rate"] == 50.0
    assert metrics["mae"] == 3.0
    assert round(metrics["rmse"], 4) == round((20.0 / 2) ** 0.5, 4)
    assert metrics["mape"] == 3.0
    assert metrics["mean_signed_error"] == -1.0


def test_compute_accuracy_metrics_handles_empty_frames():
    metrics = compute_accuracy_metrics(pd.DataFrame())
    assert metrics["samples"] == 0
    assert metrics["direction_hit_rate"] is None
    assert metrics["mae"] is None


def test_summarize_gmp_history_calculates_final_values():
    frame = pd.DataFrame(
        [
            {"name": "Alpha", "observation_at": "2026-10-01T00:00:00Z", "gmp": 10.0},
            {"name": "Alpha", "observation_at": "2026-10-02T00:00:00Z", "gmp": 15.0},
        ]
    )
    summary = summarize_gmp_history(frame)
    row = summary.iloc[0]

    assert row["name"] == "Alpha"
    assert row["observations"] == 2
    assert row["min_gmp"] == 10.0
    assert row["max_gmp"] == 15.0
    assert row["final_gmp"] == 15.0
    assert row["gmp_volatility"] == 2.5


def test_enriched_results_get_gmp_context_and_bucket():
    results = pd.DataFrame([{"name": "Alpha", "direction_accuracy": True}])
    summary = pd.DataFrame([{"name": "Alpha", "final_gmp": 12.0}])

    enriched = add_gmp_context_to_results(results, summary)
    bucketed = add_gmp_bucket_column(enriched)

    assert bucketed.loc[0, "final_gmp"] == 12.0
    assert bucketed.loc[0, "gmp_bucket"] == "> 10%"


def test_accuracy_by_bucket_groups_outcomes():
    results = pd.DataFrame(
        [
            {"gmp_bucket": "> 10%", "direction_accuracy": True},
            {"gmp_bucket": "> 10%", "direction_accuracy": False},
            {"gmp_bucket": "1% - 5%", "direction_accuracy": True},
        ]
    )
    grouped = accuracy_by_bucket(results)

    assert len(grouped) == 2
    large = grouped[grouped["gmp_bucket"] == "> 10%"].iloc[0]
    assert large["samples"] == 2
    assert large["direction_hit_rate"] == 50.0
