import smtplib
from email.message import EmailMessage

import pytest

from app.services.email_service import build_report_message, send_report


def test_build_report_message_includes_plain_text_html_and_inline_snapshot():
    message = build_report_message(
        sender="reports@example.com",
        recipient="owner@example.com",
        report="IPO Pulse Daily Report\nAlpha IPO",
        html_report="<html><body><strong>Alpha IPO</strong></body></html>",
        snapshot_png=b"png-bytes",
    )

    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "IPO Pulse Daily Report"
    assert message["From"] == "reports@example.com"
    assert message["To"] == "owner@example.com"
    assert message.get_body(preferencelist=("plain",)).get_content() == "IPO Pulse Daily Report\nAlpha IPO\n"
    html_body = message.get_body(preferencelist=("html",))
    assert html_body is not None
    assert "Alpha IPO" in html_body.get_content()
    assert any(part.get_content_type() == "image/png" for part in message.walk())


def test_send_report_uses_gmail_smtp_ssl_with_credentials_from_arguments(monkeypatch):
    smtp_calls = []
    context = object()

    class FakeSMTP:
        def __init__(self, host, port, *, context, timeout):
            smtp_calls.append(("connect", host, port, context, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, username, password):
            smtp_calls.append(("login", username, password))

        def send_message(self, message):
            smtp_calls.append(("send", message))

    monkeypatch.setattr("app.services.email_service.ssl.create_default_context", lambda: context)
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP_SSL", FakeSMTP)

    send_report(
        report="IPO Pulse Daily Report",
        sender="reports@example.com",
        app_password="abcd efgh ijkl mnop",
        recipient="owner@example.com",
        html_report="<html><body>IPO Pulse</body></html>",
        snapshot_png=b"png-bytes",
    )

    assert smtp_calls[0] == ("connect", "smtp.gmail.com", 465, context, 30)
    assert smtp_calls[1] == ("login", "reports@example.com", "abcdefghijklmnop")
    assert smtp_calls[2][0] == "send"
    message = smtp_calls[2][1]
    assert isinstance(message, EmailMessage)
    assert message["To"] == "owner@example.com"
    assert message["Subject"] == "IPO Pulse Daily Report"


def test_send_report_fails_clearly_when_required_environment_values_are_missing():
    with pytest.raises(ValueError, match="GMAIL_SENDER, GMAIL_RECIPIENT") as error:
        send_report(
            report="Report",
            sender="",
            app_password="never-print-this-password",
            recipient="",
        )

    assert "never-print-this-password" not in str(error.value)


def test_send_report_identifies_missing_app_password():
    with pytest.raises(ValueError, match="GMAIL_APP_PASSWORD"):
        send_report(
            report="Report",
            sender="reports@example.com",
            app_password="",
            recipient="owner@example.com",
        )


def test_send_report_does_not_expose_app_password_on_smtp_error(monkeypatch):
    secret = "abcdefghijklmnop"

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, *_args):
            raise smtplib.SMTPAuthenticationError(535, b"authentication failed")

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP_SSL", FakeSMTP)

    with pytest.raises(RuntimeError, match="Gmail SMTP could not send") as error:
        send_report(
            report="Report",
            sender="reports@example.com",
            app_password=secret,
            recipient="owner@example.com",
        )

    assert secret not in str(error.value)
