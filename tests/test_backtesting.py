import pandas as pd

from app.services.backtesting import calculate_baseline_metrics, load_baseline_csv


def test_load_baseline_csv_returns_known_rows(tmp_path):
    path = tmp_path / "baseline.csv"
    path.write_text(
        "ipo_name,listing_date,issue_price,pre_listing_gmp_percent,actual_listing_price,nifty_return_percent,source_url\n"
        "Alpha,2026-10-01,100,25,125,5,https://example\n"
    )
    frame = load_baseline_csv(path)
    assert len(frame) == 1
    assert frame.loc[0, "actual_listing_return_percent"] == 25.0


def test_calculate_baseline_metrics_computes_direction_and_alpha():
    frame = pd.DataFrame(
        [
            {"pre_listing_gmp_percent": 25.0, "actual_listing_return_percent": 20.0, "nifty_return_percent": 5.0},
            {"pre_listing_gmp_percent": -5.0, "actual_listing_return_percent": -2.0, "nifty_return_percent": -1.0},
        ]
    )
    metrics = calculate_baseline_metrics(frame)
    assert metrics.samples == 2
    assert metrics.direction_hit_rate == 100.0
    assert round(metrics.mean_actual_return, 3) == 9.0
    assert round(metrics.mean_alpha_vs_nifty, 3) == 7.0


def test_load_missing_file_is_graceful(tmp_path):
    frame = load_baseline_csv(tmp_path / "missing.csv")
    assert frame.empty
