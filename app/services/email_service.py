"""Gmail SMTP delivery for IPO Pulse reports."""

from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 30


def build_report_message(
    sender: str,
    recipient: str,
    report: str,
    html_report: str | None = None,
    snapshot_png: bytes | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "IPO Pulse Daily Report"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(report)
    html_body = html_report or (
        "<!doctype html><html><body style=\"font-family:Arial,sans-serif\">"
        + html.escape(report).replace("\n", "<br>")
        + "</body></html>"
    )
    message.add_alternative(html_body, subtype="html")
    if snapshot_png:
        message.get_body(preferencelist=("html",)).add_related(
            snapshot_png, maintype="image", subtype="png", cid="<ipo-pulse-dashboard>"
        )
    return message


def send_report(
    report: str,
    sender: str,
    app_password: str,
    recipient: str,
    html_report: str | None = None,
    snapshot_png: bytes | None = None,
) -> None:
    required = {
        "GMAIL_SENDER": sender,
        "GMAIL_APP_PASSWORD": app_password,
        "GMAIL_RECIPIENT": recipient,
    }
    missing = [name for name, value in required.items() if not value or not value.strip()]
    if missing:
        raise ValueError(f"Missing required email environment variable(s): {', '.join(missing)}")

    message = build_report_message(sender, recipient, report, html_report, snapshot_png)
    normalized_app_password = "".join(app_password.split())
    try:
        with smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT,
            context=ssl.create_default_context(),
            timeout=SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            smtp.login(sender, normalized_app_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise RuntimeError(
            "Gmail SMTP could not send the IPO Pulse report. Check the Gmail sender, "
            "App Password, and SMTP access."
        ) from error
