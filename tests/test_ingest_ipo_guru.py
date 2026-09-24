from datetime import timezone

import pytest

from scripts.ingest_ipo_guru import parse_observation_at


def test_parse_provider_ist_timestamp_as_utc():
    timestamp = parse_observation_at("2026-09-25 14:00:00")

    assert timestamp.isoformat() == "2026-09-25T08:30:00+00:00"
    assert timestamp.tzinfo == timezone.utc


def test_parse_provider_utc_timestamp():
    timestamp = parse_observation_at("2026-09-25T14:00:00+00:00")

    assert timestamp.isoformat() == "2026-09-25T14:00:00+00:00"


def test_parse_observation_at_requires_provider_timestamp():
    with pytest.raises(ValueError, match="updated_at is required"):
        parse_observation_at(None)