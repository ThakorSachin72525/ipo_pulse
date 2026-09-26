from datetime import date

from app.models.ipo_model import GMPObservation, IPO
from app.repositories.supabase_repository import build_prediction_payload
from app.services.ipo_service import IPOService
from scripts.ingest_ipo_guru import main


def test_ipo_service_selects_latest_pre_listing_gmp_and_builds_prediction():
    ipo = IPO(
        id="IP-300",
        name="Prediction IPO",
        issue_price=100.0,
        lot_size=100,
        listing_date=date(2026, 9, 30),
    )

    observations = [
        GMPObservation(ipo_id=ipo.id, date=date(2026, 9, 20), gmp=20.0, gmp_percent=20.0),
        GMPObservation(ipo_id=ipo.id, date=date(2026, 9, 25), gmp=30.0, gmp_percent=30.0),
    ]

    latest = IPOService.latest_pre_listing_gmp(ipo, observations)
    prediction = IPOService.create_prediction(ipo, latest)

    assert latest.gmp == 30.0
    assert prediction.expected_listing_price == 130.0
    assert prediction.expected_profit == 3000.0
    assert prediction.expected_return == 30.0


def test_ipo_service_ignores_observations_from_other_ipos():
    ipo = IPO(
        id="IP-302",
        name="Target IPO",
        issue_price=100.0,
        listing_date=date(2026, 9, 30),
    )
    observations = [
        GMPObservation(ipo_id="IP-other", date=date(2026, 9, 29), gmp=99.0, gmp_percent=99.0),
        GMPObservation(ipo_id=ipo.id, date=date(2026, 9, 20), gmp=20.0, gmp_percent=20.0),
    ]

    assert IPOService.latest_pre_listing_gmp(ipo, observations).gmp == 20.0


def test_build_prediction_payload_tracks_the_source_gmp_snapshot():
    ipo = IPO(
        id="IP-301",
        name="Payload IPO",
        issue_price=80.0,
        lot_size=250,
        listing_date=date(2026, 10, 1),
    )
    gmp = GMPObservation(
        ipo_id=ipo.id,
        date=date(2026, 9, 28),
        gmp=20.0,
        gmp_percent=25.0,
    )

    payload = build_prediction_payload(
        ipo_id=ipo.id,
        gmp_history_id="gmp-uuid-123",
        ipo=ipo,
        gmp=gmp,
    )

    assert payload["ipo_id"] == ipo.id
    assert payload["gmp_history_id"] == "gmp-uuid-123"
    assert payload["gmp_value"] == 20.0
    assert payload["expected_listing_price"] == 100.0
    assert payload["expected_profit"] == 5000.0
    assert payload["expected_return"] == 25.0


def test_main_persists_prediction_rows_from_each_live_gmp_snapshot(monkeypatch):
    calls: list[tuple[str, str, str | None]] = []

    class FakeRepository:
        def __init__(self):
            self.ipo_id = "ipo-999"
            self.gmp_history_id = "gmp-999"

        def upsert_ipo(self, record):
            return self.ipo_id

        def upsert_gmp_observation(self, ipo_id, observation_at, record):
            calls.append(("gmp", ipo_id, record["gmp"]))
            return self.gmp_history_id

        def upsert_prediction(self, ipo_id, gmp_history_id, ipo, gmp):
            calls.append(("prediction", ipo_id, gmp_history_id))
            assert gmp.ipo_id == ipo_id
            assert ipo.issue_price == 100.0
            assert gmp.gmp == 25.0
            return "prediction-999"

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def fetch_gmp(self):
            return {
                "data": [
                    {
                        "name": "Live Prediction IPO",
                        "issue_price": "100",
                        "lot_size": 100,
                        "listing_date": "2026-11-02",
                        "gmp": {"price": "25", "percentage": "25", "updated_at": "2026-10-28T10:00:00+05:30"},
                        "status": "open",
                    }
                ]
            }

    monkeypatch.setattr(
        "scripts.ingest_ipo_guru.Settings.from_env",
        lambda: type("Settings", (), {"ipo_api_key": "demo-key", "supabase_url": "https://x", "supabase_key": "key"})(),
    )
    monkeypatch.setattr("scripts.ingest_ipo_guru.IPOGuruClient", FakeClient)
    monkeypatch.setattr("scripts.ingest_ipo_guru.SupabaseRepository.from_settings", lambda settings: FakeRepository())

    exit_code = main()

    assert exit_code == 0
    assert ("gmp", "ipo-999", 25.0) in calls
    assert ("prediction", "ipo-999", "gmp-999") in calls


def test_main_does_not_predict_without_valid_issue_price_or_before_listing(monkeypatch):
    gmp_calls = []
    prediction_calls = []

    class FakeRepository:
        def upsert_ipo(self, record):
            return record["name"]

        def upsert_gmp_observation(self, ipo_id, observation_at, record):
            gmp_calls.append(ipo_id)
            return f"gmp-{ipo_id}"

        def upsert_prediction(self, *args):
            prediction_calls.append(args)

    class FakeClient:
        def __init__(self, api_key):
            pass

        def fetch_gmp(self):
            return {
                "data": [
                    {
                        "name": "Missing Price IPO",
                        "issue_price": None,
                        "gmp": {"price": "10", "percentage": "10", "updated_at": "2026-09-20T10:00:00+05:30"},
                    },
                    {
                        "name": "Already Listed IPO",
                        "issue_price": "100",
                        "listing_date": "2026-09-20",
                        "gmp": {"price": "10", "percentage": "10", "updated_at": "2026-09-21T10:00:00+05:30"},
                    },
                ]
            }

    monkeypatch.setattr(
        "scripts.ingest_ipo_guru.Settings.from_env",
        lambda: type("Settings", (), {"ipo_api_key": "demo-key", "supabase_url": "https://x", "supabase_key": "key"})(),
    )
    monkeypatch.setattr("scripts.ingest_ipo_guru.IPOGuruClient", FakeClient)
    monkeypatch.setattr(
        "scripts.ingest_ipo_guru.SupabaseRepository.from_settings",
        lambda _settings: FakeRepository(),
    )

    assert main() == 0
    assert len(gmp_calls) == 2
    assert prediction_calls == []
