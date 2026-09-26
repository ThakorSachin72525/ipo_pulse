"""Simple daily report generation for IPO Pulse."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import fmean


def build_daily_report(
    current_ipos: Iterable[Mapping[str, object]] | None = None,
    recent_results: Iterable[Mapping[str, object]] | None = None,
) -> str:
    """Return a plain-text report for the current IPO state and recent listing outcomes."""
    current_rows = list(current_ipos or [])
    result_rows = list(recent_results or [])

    lines = [
        "IPO Pulse Daily Report",
        "======================",
        "",
        "Current IPOs:",
    ]

    if current_rows:
        for row in current_rows:
            gmp = row.get("gmp")
            price = row.get("estimated_listing_price")
            status = row.get("status", "open")
            lines.append(f"- {row.get('name', 'IPO')}: status={status}, GMP={gmp}, estimated_listing={price}")
    else:
        lines.append("- No active IPOs available.")

    lines.extend(["", "Recent listing outcomes:", "Direction summary:"])
    if result_rows:
        for row in result_rows:
            name = row.get("name", "IPO")
            actual = row.get("actual_listing_price")
            predicted = row.get("predicted_listing_price")
            error = row.get("percentage_error")
            direction = "up" if row.get("direction_accuracy") else "down"
            lines.append(
                f"- {name}: actual={actual}, predicted={predicted}, error={error}%, Direction={direction}"
            )
    else:
        lines.append("- No recent listing results available.")

    direction_results = [
        row["direction_accuracy"]
        for row in result_rows
        if isinstance(row.get("direction_accuracy"), bool)
    ]
    percentage_errors = [
        row["percentage_error"]
        for row in result_rows
        if isinstance(row.get("percentage_error"), (int, float))
    ]
    direction_rate = (
        f"{sum(direction_results)}/{len(direction_results)} ({fmean(direction_results) * 100:.1f}%)"
        if direction_results
        else "N/A"
    )
    mean_error = f"{fmean(percentage_errors):.2f}%" if percentage_errors else "N/A"
    lines.extend(
        [
            "",
            "Overall accuracy:",
            f"Direction accuracy: {direction_rate}",
            f"Mean percentage error: {mean_error}",
            "",
            "Summary:",
            f"Current IPO count: {len(current_rows)}",
            f"Recent result count: {len(result_rows)}",
        ]
    )
    return "\n".join(lines)
