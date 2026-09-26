from datetime import date

from app.models.ipo_model import GMPObservation, IPO
from app.repositories.supabase_repository import SupabaseRepository, build_prediction_payload


def test_prediction_payload_round_trips_the_linked_gmp_snapshot():
    ipo = IPO(
        id="IP-401",
        name="Persisted Prediction IPO",
        issue_price=120.0,
        lot_size=50,
        listing_date=date(2026, 11, 1),
    )
    gmp = GMPObservation(
        ipo_id=ipo.id,
        date=date(2026, 10, 25),
        gmp=30.0,
        gmp_percent=25.0,
    )

    payload = build_prediction_payload(
        ipo_id=ipo.id,
        gmp_history_id="gmp-row-abc",
        ipo=ipo,
        gmp=gmp,
    )

    assert payload["gmp_history_id"] == "gmp-row-abc"
    assert payload["expected_listing_price"] == 150.0
    assert payload["expected_profit"] == 1500.0
    assert payload["expected_return"] == 25.0
    assert payload["gmp_date"] == "2026-10-25"


def test_repository_upserts_prediction_with_its_gmp_foreign_key():
    class Query:
        def upsert(self, payload, on_conflict):
            assert payload["gmp_history_id"] == "gmp-row-abc"
            assert on_conflict == "ipo_id,gmp_history_id,source"
            return self

        def execute(self):
            return type("Response", (), {"data": [{"prediction_id": "prediction-abc"}]})()

    class Client:
        def table(self, name):
            assert name == "ipo_predictions"
            return Query()

    ipo = IPO(id="IP-402", name="Upsert IPO", issue_price=100.0, lot_size=10)
    gmp = GMPObservation(ipo_id=ipo.id, date=date(2026, 10, 25), gmp=15.0, gmp_percent=15.0)

    prediction_id = SupabaseRepository(Client()).upsert_prediction(
        ipo.id, "gmp-row-abc", ipo, gmp
    )

    assert prediction_id == "prediction-abc"
