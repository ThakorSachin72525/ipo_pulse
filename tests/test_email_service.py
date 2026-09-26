import base64
from email.message import EmailMessage

import pytest

from app.services.email_service import (
    build_report_message,
    fetch_google_access_token,
    load_recipients,
    send_report,
)


def test_load_recipients_reads_one_address_per_line_and_deduplicates(tmp_path):
    recipients_file = tmp_path / "report_recipients.txt"
    recipients_file.write_text(
        "# Daily report recipients\nowner@example.com\n\nowner@example.com\nteam@example.com\n"
    )

    assert load_recipients(recipients_file) == ["owner@example.com", "team@example.com"]


def test_load_recipients_rejects_invalid_addresses(tmp_path):
    recipients_file = tmp_path / "report_recipients.txt"
    recipients_file.write_text("not-an-email\n")

    with pytest.raises(ValueError, match="Invalid recipient on line 1"):
        load_recipients(recipients_file)


def test_build_report_message_includes_plain_text_and_html():
    message = build_report_message(
        sender="reports@example.com",
        recipient="owner@example.com",
        report="IPO Pulse Daily Report\nAlpha IPO",
    )

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "IPO Pulse Daily Report"
    assert message.get_body(preferencelist=("plain",)).get_content() == "IPO Pulse Daily Report\nAlpha IPO\n"
    html_body = message.get_body(preferencelist=("html",))
    assert html_body is not None
    assert "Alpha IPO" in html_body.get_content()


def test_fetch_google_access_token_uses_refresh_token(monkeypatch):
    requests_seen = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "short-lived-access-token"}

    def fake_post(url, data, timeout):
        requests_seen.append((url, data, timeout))
        return Response()

    monkeypatch.setattr("app.services.email_service.requests.post", fake_post)

    token = fetch_google_access_token(
        client_id="oauth-client-id",
        client_secret="oauth-client-secret",
        refresh_token="long-lived-refresh-token",
    )

    assert token == "short-lived-access-token"
    assert requests_seen[0][0] == "https://oauth2.googleapis.com/token"
    assert requests_seen[0][1] == {
        "client_id": "oauth-client-id",
        "client_secret": "oauth-client-secret",
        "refresh_token": "long-lived-refresh-token",
        "grant_type": "refresh_token",
    }


def test_send_report_uses_gmail_api_and_fails_without_credentials(monkeypatch):
    requests_seen = []

    class Response:
        def raise_for_status(self):
            pass

    def fake_post(url, headers, json, timeout):
        requests_seen.append((url, headers, json, timeout))
        return Response()

    monkeypatch.setattr("app.services.email_service.requests.post", fake_post)
    monkeypatch.setattr(
        "app.services.email_service.fetch_google_access_token",
        lambda *_args: "short-lived-access-token",
    )
    send_report(
        report="IPO Pulse Daily Report",
        sender="reports@example.com",
        client_id="oauth-client-id",
        client_secret="oauth-client-secret",
        refresh_token="long-lived-refresh-token",
        recipient="owner@example.com",
    )

    assert len(requests_seen) == 1
    url, headers, payload, timeout = requests_seen[0]
    assert url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert headers["Authorization"] == "Bearer short-lived-access-token"
    assert timeout == 30
    message = base64.urlsafe_b64decode(payload["raw"])
    assert b"To: owner@example.com" in message
    assert b"Subject: IPO Pulse Daily Report" in message
    assert b"IPO Pulse Daily Report" in message

    with pytest.raises(ValueError, match="email credentials and recipient"):
        send_report(
            report="Report",
            sender="",
            client_id="",
            client_secret="",
            refresh_token="",
            recipient="",
        )
