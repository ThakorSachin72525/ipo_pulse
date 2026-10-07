"""Print or email a snapshot of the IPO Pulse dashboard."""

from __future__ import annotations

import argparse
from app.config import Settings
from app.repositories.supabase_repository import SupabaseRepository
from app.services.email_service import send_report
from app.services.report_service import (
    build_daily_report,
    build_dashboard_email_html,
    build_dashboard_snapshot_png,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send",
        action="store_true",
        help="send the dashboard email through Gmail SMTP; without this flag print its text fallback",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    repository = SupabaseRepository.from_settings(settings)
    current_ipos, recent_results = repository.get_daily_report_data()
    report = build_daily_report(current_ipos, recent_results)
    html_report = build_dashboard_email_html(current_ipos, recent_results)
    snapshot_png = build_dashboard_snapshot_png(current_ipos, recent_results)

    if not args.send:
        print(report)
        print("\nDry run: no email sent.")
        return 0

    send_report(
        report=report,
        sender=settings.gmail_sender or "",
        app_password=settings.gmail_app_password or "",
        recipient=settings.gmail_recipient or "",
        html_report=html_report,
        snapshot_png=snapshot_png,
    )
    print("Dashboard email sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())