"""Print or email the latest IPO Pulse report."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import Settings
from app.repositories.supabase_repository import SupabaseRepository
from app.services.email_service import load_recipients, send_report
from app.services.report_service import build_daily_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send",
        action="store_true",
        help="send the report by Gmail SMTP; without this flag the report is printed only",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    repository = SupabaseRepository.from_settings(settings)
    current_ipos, recent_results = repository.get_daily_report_data()
    report = build_daily_report(current_ipos, recent_results)

    if not args.send:
        print(report)
        print("\nDry run: no email sent.")
        return 0

    oauth_credentials = (
        settings.email_sender,
        settings.google_oauth_client_id,
        settings.google_oauth_client_secret,
        settings.google_oauth_refresh_token,
    )
    if not all(oauth_credentials):
        raise RuntimeError(
            "EMAIL_SENDER, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, "
            "and GOOGLE_OAUTH_REFRESH_TOKEN are required with --send"
        )
    recipient_file = Path(__file__).resolve().parents[1] / "config" / "report_recipients.txt"
    recipients = load_recipients(recipient_file)
    if not recipients:
        raise RuntimeError(f"Add at least one recipient to {recipient_file}")
    for recipient in recipients:
        send_report(
            report=report,
            sender=settings.email_sender,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            refresh_token=settings.google_oauth_refresh_token,
            recipient=recipient,
        )
    print(f"Daily report sent to {len(recipients)} recipient(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())