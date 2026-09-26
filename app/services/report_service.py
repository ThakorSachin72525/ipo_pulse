"""Build text and HTML snapshots of the IPO Pulse dashboard."""

from __future__ import annotations

import html
import math
from collections.abc import Iterable, Mapping
from statistics import fmean


DASHBOARD_URL = "https://ipopulse-dashboard.streamlit.app"


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _money(value: object) -> str:
    number = _number(value)
    return "—" if number is None else f"₹{number:,.2f}"


def _percent(value: object) -> str:
    number = _number(value)
    return "—" if number is None else f"{number:.2f}%"


def build_daily_report(
    current_ipos: Iterable[Mapping[str, object]] | None = None,
    recent_results: Iterable[Mapping[str, object]] | None = None,
) -> str:
    """Return a plain-text fallback for the daily dashboard email."""
    current_rows = list(current_ipos or [])
    result_rows = list(recent_results or [])

    lines = [
        "IPO Pulse Daily Dashboard",
        "=========================",
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

    lines.extend(["", "Recent listing outcomes:"])
    if result_rows:
        for row in result_rows:
            name = row.get("name", "IPO")
            actual = row.get("actual_listing_price")
            predicted = row.get("predicted_listing_price")
            error = row.get("percentage_error")
            direction = "correct" if row.get("direction_accuracy") is True else "incorrect"
            lines.append(
                f"- {name}: actual={actual}, predicted={predicted}, error={error}%, Direction={direction}"
            )
    else:
        lines.append("- No recent listing outcomes available.")

    direction_results = [
        row["direction_accuracy"]
        for row in result_rows
        if isinstance(row.get("direction_accuracy"), bool)
    ]
    percentage_errors = [
        number
        for row in result_rows
        if (number := _number(row.get("percentage_error"))) is not None
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
            "Accuracy:",
            f"Direction accuracy: {direction_rate}",
            f"Mean percentage error: {mean_error}",
            "",
            f"Open live dashboard: {DASHBOARD_URL}",
            f"Tracked IPO count: {len(current_rows)}",
            f"Recent outcome count: {len(result_rows)}",
        ]
    )
    return "\n".join(lines)


def build_dashboard_email_html(
    current_ipos: Iterable[Mapping[str, object]] | None = None,
    recent_results: Iterable[Mapping[str, object]] | None = None,
    dashboard_url: str = DASHBOARD_URL,
) -> str:
    """Render a table-based, email-client-safe dashboard snapshot."""
    current_rows = list(current_ipos or [])
    result_rows = list(recent_results or [])
    direction_results = [
        row["direction_accuracy"]
        for row in result_rows
        if isinstance(row.get("direction_accuracy"), bool)
    ]
    percentage_errors = [
        number
        for row in result_rows
        if (number := _number(row.get("percentage_error"))) is not None
    ]
    accuracy = (
        f"{sum(direction_results)}/{len(direction_results)} "
        f"({fmean(direction_results) * 100:.1f}%)"
        if direction_results
        else "N/A"
    )
    mean_error = f"{fmean(percentage_errors):.2f}%" if percentage_errors else "N/A"

    ipo_rows = "".join(
        "<tr>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;color:#17243b;font-weight:600'>{html.escape(str(row.get('name') or 'IPO'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;color:#536178'>{html.escape(str(row.get('status') or '—'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;text-align:right;color:#17243b'>{_money(row.get('gmp'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;text-align:right;color:#17243b'>{_money(row.get('estimated_listing_price'))}</td>"
        "</tr>"
        for row in current_rows
    ) or (
        "<tr><td colspan='4' style='padding:16px 12px;color:#64748b'>"
        "No current IPO data is available.</td></tr>"
    )

    result_rows_html = "".join(
        "<tr>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;color:#17243b;font-weight:600'>{html.escape(str(row.get('name') or 'IPO'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;text-align:right;color:#17243b'>{_money(row.get('predicted_listing_price'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;text-align:right;color:#17243b'>{_money(row.get('actual_listing_price'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;text-align:right;color:#17243b'>{_percent(row.get('percentage_error'))}</td>"
        f"<td style='padding:11px 12px;border-bottom:1px solid #e5eaf1;color:#536178'>{'Correct' if row.get('direction_accuracy') is True else 'Incorrect' if row.get('direction_accuracy') is False else 'N/A'}</td>"
        "</tr>"
        for row in result_rows
    ) or (
        "<tr><td colspan='5' style='padding:16px 12px;color:#64748b'>"
        "No listing outcomes are available yet.</td></tr>"
    )

    safe_url = html.escape(dashboard_url, quote=True)
    return f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#17243b">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f1f5f9;padding:24px 10px">
<tr><td align="center">
<table role="presentation" width="720" cellspacing="0" cellpadding="0" style="width:100%;max-width:720px;background:#ffffff;border-radius:14px;overflow:hidden">
<tr><td style="padding:28px 30px;background:#14243d;color:#ffffff">
<div style="font-size:12px;letter-spacing:2px;font-weight:700;color:#9db4d4">IPO PULSE</div>
<div style="font-size:27px;line-height:1.25;font-weight:700;padding-top:8px">Daily Dashboard</div>
<div style="font-size:14px;line-height:1.5;color:#d1dced;padding-top:6px">IPO activity, GMP snapshots, and listing accuracy</div>
</td></tr>
<tr><td style="padding:22px 30px 8px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
<td width="50%" style="padding:8px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="background:#f5f8fc;border:1px solid #e5eaf1;border-radius:10px;padding:15px"><div style="font-size:12px;color:#64748b">Tracked IPOs</div><div style="font-size:25px;font-weight:700;padding-top:5px;color:#17243b">{len(current_rows)}</div></td></tr></table></td>
<td width="50%" style="padding:8px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="background:#f5f8fc;border:1px solid #e5eaf1;border-radius:10px;padding:15px"><div style="font-size:12px;color:#64748b">Recent outcomes</div><div style="font-size:25px;font-weight:700;padding-top:5px;color:#17243b">{len(result_rows)}</div></td></tr></table></td>
</tr><tr>
<td width="50%" style="padding:8px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="background:#f5f8fc;border:1px solid #e5eaf1;border-radius:10px;padding:15px"><div style="font-size:12px;color:#64748b">Direction accuracy</div><div style="font-size:22px;font-weight:700;padding-top:5px;color:#167a62">{accuracy}</div></td></tr></table></td>
<td width="50%" style="padding:8px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="background:#f5f8fc;border:1px solid #e5eaf1;border-radius:10px;padding:15px"><div style="font-size:12px;color:#64748b">Mean percentage error</div><div style="font-size:22px;font-weight:700;padding-top:5px;color:#17243b">{mean_error}</div></td></tr></table></td>
</tr></table>
</td></tr>
<tr><td style="padding:12px 30px 4px;font-size:19px;font-weight:700;color:#17243b">Current IPO overview</td></tr>
<tr><td style="padding:8px 30px 18px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px">
<thead><tr style="background:#edf2f8;text-align:left"><th style="padding:10px 12px">IPO</th><th style="padding:10px 12px">Status</th><th style="padding:10px 12px;text-align:right">GMP</th><th style="padding:10px 12px;text-align:right">Est. listing</th></tr></thead><tbody>{ipo_rows}</tbody></table></td></tr>
<tr><td style="padding:8px 30px 4px;font-size:19px;font-weight:700;color:#17243b">Predicted versus actual listings</td></tr>
<tr><td style="padding:8px 30px 22px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px">
<thead><tr style="background:#edf2f8;text-align:left"><th style="padding:10px 12px">IPO</th><th style="padding:10px 12px;text-align:right">Predicted</th><th style="padding:10px 12px;text-align:right">Actual</th><th style="padding:10px 12px;text-align:right">Error</th><th style="padding:10px 12px">Direction</th></tr></thead><tbody>{result_rows_html}</tbody></table></td></tr>
<tr><td style="padding:0 30px 16px"><img src="cid:ipo-pulse-dashboard" alt="IPO Pulse dashboard snapshot" width="660" style="display:block;width:100%;max-width:660px;height:auto;border:1px solid #e5eaf1;border-radius:8px"></td></tr>
<tr><td align="center" style="padding:4px 30px 28px"><a href="{safe_url}" style="display:inline-block;padding:13px 22px;background:#2563eb;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;border-radius:8px">Open live dashboard</a></td></tr>
<tr><td style="padding:16px 30px;background:#f5f8fc;color:#64748b;font-size:11px;line-height:1.5">GMP is market sentiment, not a guaranteed listing price. This email is a snapshot; open the live dashboard for the interactive view.</td></tr>
</table>
</td></tr></table>
</body>
</html>"""


def build_dashboard_snapshot_png(
    current_ipos: Iterable[Mapping[str, object]] | None = None,
    recent_results: Iterable[Mapping[str, object]] | None = None,
) -> bytes:
    """Render a static dashboard snapshot for inline email display."""
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    current_rows = list(current_ipos or [])
    result_rows = list(recent_results or [])
    width = 1200
    row_height = 44
    current_count = max(1, len(current_rows))
    result_count = max(1, len(result_rows))
    height = 160 + 250 + 64 + current_count * row_height + 64 + result_count * row_height + 90
    image = Image.new("RGB", (width, height), "#f1f5f9")
    draw = ImageDraw.Draw(image)

    try:
        regular = ImageFont.truetype("DejaVuSans.ttf", 18)
        small = ImageFont.truetype("DejaVuSans.ttf", 15)
        heading = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        metric = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        label = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
    except OSError:
        regular = ImageFont.load_default(size=18)
        small = ImageFont.load_default(size=15)
        heading = ImageFont.load_default(size=28)
        metric = ImageFont.load_default(size=30)
        label = ImageFont.load_default(size=13)

    def fit(text: object, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> str:
        value = str(text)
        while len(value) > 4 and draw.textbbox((0, 0), value, font=font)[2] > max_width:
            value = value[:-2] + "…"
        return value

    def draw_card(x: int, y: int, title: str, value: str, accent: str) -> None:
        draw.rounded_rectangle((x, y, x + 520, y + 94), radius=12, fill="#ffffff", outline="#dce4ee", width=2)
        draw.text((x + 20, y + 16), title.upper(), font=label, fill="#64748b")
        draw.text((x + 20, y + 42), fit(value, metric, 470), font=metric, fill=accent)

    direction_results = [
        row["direction_accuracy"]
        for row in result_rows
        if isinstance(row.get("direction_accuracy"), bool)
    ]
    errors = [
        number
        for row in result_rows
        if (number := _number(row.get("percentage_error"))) is not None
    ]
    accuracy = (
        f"{sum(direction_results)}/{len(direction_results)} ({fmean(direction_results) * 100:.1f}%)"
        if direction_results
        else "N/A"
    )
    mean_error = f"{fmean(errors):.2f}%" if errors else "N/A"

    draw.rounded_rectangle((0, 0, width, 145), radius=0, fill="#14243d")
    draw.text((60, 32), "IPO PULSE", font=label, fill="#9db4d4")
    draw.text((60, 58), "Daily Dashboard", font=heading, fill="#ffffff")
    draw.text((60, 105), "IPO activity, GMP snapshots, and listing accuracy", font=small, fill="#d1dced")

    draw_card(60, 170, "Tracked IPOs", str(len(current_rows)), "#17243b")
    draw_card(620, 170, "Recent outcomes", str(len(result_rows)), "#17243b")
    draw_card(60, 280, "Direction accuracy", accuracy, "#167a62")
    draw_card(620, 280, "Mean percentage error", mean_error, "#17243b")

    y = 410
    draw.text((60, y), "Current IPO overview", font=heading, fill="#17243b")
    y += 48
    columns = [(60, 500), (560, 180), (740, 190), (930, 210)]
    draw.rounded_rectangle((60, y, 1140, y + 38), radius=5, fill="#e5edf6")
    for (x, _), title in zip(columns, ("IPO", "STATUS", "GMP", "EST. LISTING")):
        draw.text((x + 10, y + 11), title, font=label, fill="#475569")
    y += 38
    for index, row in enumerate(current_rows or [{}]):
        if index % 2 == 0:
            draw.rectangle((60, y, 1140, y + row_height), fill="#ffffff")
        values = (
            row.get("name") or ("No current IPO data is available." if not current_rows else "IPO"),
            row.get("status") or "—",
            "INR —" if _number(row.get("gmp")) is None else f"INR {_number(row.get('gmp')):,.2f}",
            "INR —" if _number(row.get("estimated_listing_price")) is None else f"INR {_number(row.get('estimated_listing_price')):,.2f}",
        )
        for (x, cell_width), value in zip(columns, values):
            draw.text((x + 10, y + 13), fit(value, small, cell_width - 20), font=small, fill="#17243b")
        draw.line((60, y + row_height, 1140, y + row_height), fill="#e5eaf1", width=1)
        y += row_height

    y += 25
    draw.text((60, y), "Predicted versus actual listings", font=heading, fill="#17243b")
    y += 48
    result_columns = [(60, 440), (500, 170), (670, 170), (840, 150), (990, 150)]
    draw.rounded_rectangle((60, y, 1140, y + 38), radius=5, fill="#e5edf6")
    for (x, _), title in zip(result_columns, ("IPO", "PREDICTED", "ACTUAL", "ERROR", "DIRECTION")):
        draw.text((x + 10, y + 11), title, font=label, fill="#475569")
    y += 38
    for index, row in enumerate(result_rows or [{}]):
        if index % 2 == 0:
            draw.rectangle((60, y, 1140, y + row_height), fill="#ffffff")
        direction = "Correct" if row.get("direction_accuracy") is True else "Incorrect" if row.get("direction_accuracy") is False else "N/A"
        values = (
            row.get("name") or ("No listing outcomes are available yet." if not result_rows else "IPO"),
            "INR —" if _number(row.get("predicted_listing_price")) is None else f"INR {_number(row.get('predicted_listing_price')):,.2f}",
            "INR —" if _number(row.get("actual_listing_price")) is None else f"INR {_number(row.get('actual_listing_price')):,.2f}",
            _percent(row.get("percentage_error")),
            direction,
        )
        for (x, cell_width), value in zip(result_columns, values):
            draw.text((x + 10, y + 13), fit(value, small, cell_width - 20), font=small, fill="#17243b")
        draw.line((60, y + row_height, 1140, y + row_height), fill="#e5eaf1", width=1)
        y += row_height

    draw.text((60, height - 42), "GMP is market sentiment, not a guaranteed listing price. Open the live dashboard for the interactive view.", font=small, fill="#64748b")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
