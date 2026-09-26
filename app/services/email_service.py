"""Email delivery for IPO Pulse reports."""

from __future__ import annotations

import html
import smtplib
import ssl
from email.utils import parseaddr
from email.message import EmailMessage
from pathlib import Path

import requests


def load_recipients(path: Path) -> list[str]:
    recipients = []
    seen = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        recipient = line.strip()
        if not recipient or recipient.startswith("#"):
            continue
        _, parsed_address = parseaddr(recipient)
        if (
            parsed_address != recipient
            or recipient.count("@") != 1
            or any(character.isspace() for character in recipient)
        ):
            raise ValueError(f"Invalid recipient on line {line_number} in {path}")
        normalized = recipient.casefold()
        if normalized not in seen:
            recipients.append(recipient)
            seen.add(normalized)
    return recipients


def build_report_message(sender: str, recipient: str, report: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "IPO Pulse Daily Report"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(report)
    escaped_report = html.escape(report)
    message.add_alternative(
        f"<!doctype html><html><body><pre>{escaped_report}</pre></body></html>",
        subtype="html",
    )
    return message


def fetch_google_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Google OAuth response did not contain an access token")
    return access_token


def send_report(
    report: str,
    sender: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    recipient: str,
) -> None:
    if not all((sender, client_id, client_secret, refresh_token, recipient)):
        raise ValueError("email credentials and recipient are required")

    access_token = fetch_google_access_token(client_id, client_secret, refresh_token)
    message = build_report_message(sender, recipient, report)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as smtp:
        auth_string = f"user={sender}\x01auth=Bearer {access_token}\x01\x01"
        smtp.auth("XOAUTH2", lambda _challenge=None: auth_string, initial_response_ok=True)
        smtp.send_message(message)