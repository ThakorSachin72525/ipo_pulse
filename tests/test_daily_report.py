import sys

import pytest

from app.services.report_service import build_daily_report
from app.repositories.supabase_repository import SupabaseRepository
from scripts import send_daily_report


def test_build_daily_report_includes_active_ipos_and_accuracy_summary():
    report = build_daily_report(
        current_ipos=[
            {"name": "Alpha IPO", "gmp": 42.5, "estimated_listing_price": 142.5, "status": "open"},
            {"name": "Beta IPO", "gmp": 5.0, "estimated_listing_price": 105.0, "status": "open"},
        ],
        recent_results=[
            {"name": "Gamma IPO", "actual_listing_price": 118.0, "predicted_listing_price": 110.0, "percentage_error": 7.27, "direction_accuracy": True},
            {"name": "Delta IPO", "actual_listing_price": 92.0, "predicted_listing_price": 110.0, "percentage_error": 19.57, "direction_accuracy": False},
        ],
    )

    assert "IPO Pulse Daily Dashboard" in report
    assert "Alpha IPO" in report
    assert "Beta IPO" in report
    assert "Gamma IPO" in report
    assert "Direction" in report
    assert "dashboard" in report.lower()
    assert "Direction accuracy: 1/2 (50.0%)" in report
    assert "Mean percentage error: 13.42%" in report


def test_repository_builds_report_rows_from_latest_gmp_and_saved_results():
    class Response:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, *_args):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            if self.table_name == "ipos":
                return Response([
                    {"ipo_id": "ipo-a", "ipo_name": "Alpha IPO", "status": "open", "source": "ipo_guru"},
                    {"ipo_id": "sample-a", "ipo_name": "Untracked Example IPO", "status": "test", "source": "manual_test"},
                ])
            if self.table_name == "ipo_gmp_history":
                return Response([
                    {"ipo_id": "sample-a", "gmp": 15.0, "estimated_listing_price": 115.0},
                    {"ipo_id": "ipo-a", "gmp": 20.0, "estimated_listing_price": 120.0},
                    {"ipo_id": "ipo-a", "gmp": 10.0, "estimated_listing_price": 110.0},
                ])
            return Response([
                {
                    "ipo_id": "sample-a",
                    "actual_listing_price": 112.0,
                    "predicted_listing_price": 115.0,
                    "percentage_error": 2.61,
                    "direction_accuracy": True,
                },
                {
                    "ipo_id": "ipo-a",
                    "actual_listing_price": 118.0,
                    "predicted_listing_price": 110.0,
                    "percentage_error": 7.27,
                    "direction_accuracy": True,
                }
            ])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    current_ipos, recent_results = SupabaseRepository(Client()).get_daily_report_data()

    assert current_ipos == [
        {"name": "Alpha IPO", "status": "open", "gmp": 20.0, "estimated_listing_price": 120.0}
    ]
    assert recent_results[0]["name"] == "Alpha IPO"
    assert recent_results[0]["direction_accuracy"] is True


def test_daily_report_command_defaults_to_dry_run(monkeypatch, capsys):
    class Settings:
        email_sender = None
        google_oauth_client_id = None
        google_oauth_client_secret = None
        google_oauth_refresh_token = None

    class Repository:
        def get_daily_report_data(self):
            return ([{"name": "Dry Run IPO", "gmp": 12.0}], [])

    monkeypatch.setattr(sys, "argv", ["send_daily_report"])
    monkeypatch.setattr(send_daily_report.Settings, "from_env", lambda: Settings())
    monkeypatch.setattr(
        send_daily_report.SupabaseRepository,
        "from_settings",
        lambda _settings: Repository(),
    )
    monkeypatch.setattr(
        send_daily_report,
        "send_report",
        lambda **_kwargs: pytest.fail("dry-run must not send email"),
    )

    assert send_daily_report.main() == 0
    output = capsys.readouterr().out
    assert "Dry Run IPO" in output
    assert "Dry run: no email sent." in output


def test_send_flag_delivers_separate_messages_to_configured_recipients(monkeypatch, capsys):
    class Settings:
        email_sender = "reports@example.com"
        google_oauth_client_id = "oauth-client-id"
        google_oauth_client_secret = "oauth-client-secret"
        google_oauth_refresh_token = "long-lived-refresh-token"

    class Repository:
        def get_daily_report_data(self):
            return ([], [])

    sent_to = []
    monkeypatch.setattr(sys, "argv", ["send_daily_report", "--send"])
    monkeypatch.setattr(send_daily_report.Settings, "from_env", lambda: Settings())
    monkeypatch.setattr(
        send_daily_report.SupabaseRepository,
        "from_settings",
        lambda _settings: Repository(),
    )
    monkeypatch.setattr(
        send_daily_report,
        "load_recipients",
        lambda _path: ["first@example.com", "second@example.com"],
    )
    monkeypatch.setattr(
        send_daily_report,
        "send_report",
        lambda **kwargs: sent_to.append(kwargs["recipient"]),
    )

    assert send_daily_report.main() == 0
    assert sent_to == ["first@example.com", "second@example.com"]
    assert "2 recipient(s)" in capsys.readouterr().out
