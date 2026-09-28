from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models.ipo_model import GMPObservation, IPO, PredictionRecord
from app.repositories.supabase_repository import SupabaseRepository, build_listing_result_payload
from app.services.ipo_service import IPOService
from scripts import reconcile_listings


def test_repository_reconciles_a_listed_ipo_to_its_latest_prediction():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def table(self, table_name):
            class Query:
                def __init__(self, table_name):
                    self.table_name = table_name

                def select(self, *_args, **_kwargs):
                    return self

                def eq(self, *_args, **_kwargs):
                    return self

                def order(self, *_args, **_kwargs):
                    return self

                def limit(self, *_args, **_kwargs):
                    return self

                def execute(self):
                    if self.table_name == "ipo_predictions":
                        return type("Response", (), {"data": [{
                            "prediction_id": "prediction-xyz",
                            "ipo_id": "IP-503",
                            "gmp_date": "2026-11-08",
                            "gmp_value": 10.0,
                            "gmp_percent": 10.0,
                            "issue_price": 100.0,
                            "lot_size": 200,
                            "expected_listing_price": 110.0,
                            "expected_profit": 2000.0,
                            "expected_return": 10.0,
                            "source": "ipo_guru",
                        }]})()
                    return type("Response", (), {"data": []})()

            return Query(table_name)

    repository = SupabaseRepository(FakeClient())

    ipo = IPO(
        id="IP-503",
        name="Reconcile IPO",
        issue_price=100.0,
        lot_size=200,
        actual_listing_price=115.0,
    )

    prediction_row = repository.find_latest_prediction(ipo.id)
    assert prediction_row is not None
    assert prediction_row["prediction_id"] == "prediction-xyz"
    assert prediction_row["expected_listing_price"] == 110.0


def test_build_listing_result_payload_tracks_the_actual_vs_predicted_outcome():
    ipo = IPO(
        id="IP-500",
        name="Accuracy IPO",
        issue_price=100.0,
        lot_size=100,
        actual_listing_price=130.0,
        listing_date=date(2026, 11, 10),
    )
    prediction = PredictionRecord(
        ipo_id=ipo.id,
        gmp_date=date(2026, 11, 8),
        gmp_value=20.0,
        gmp_percent=20.0,
        issue_price=ipo.issue_price,
        lot_size=ipo.lot_size,
        source="ipo_guru",
    )
    prediction.expected_listing_price = 120.0
    prediction.expected_profit = 2000.0
    prediction.expected_return = 20.0

    payload = build_listing_result_payload(
        ipo_id=ipo.id,
        prediction_id="prediction-500",
        ipo=ipo,
        prediction=prediction,
    )

    assert payload["ipo_id"] == ipo.id
    assert payload["prediction_id"] == "prediction-500"
    assert payload["actual_listing_price"] == 130.0
    assert payload["predicted_listing_price"] == 120.0
    assert payload["prediction_error"] == 10.0
    assert payload["percentage_error"] == 8.333333333333332
    assert payload["direction_accuracy"] is True


def test_listing_result_math_handles_a_negative_direction_case():
    ipo = IPO(
        id="IP-501",
        name="Negative Outcome IPO",
        issue_price=100.0,
        lot_size=100,
        actual_listing_price=90.0,
    )
    prediction = PredictionRecord(
        ipo_id=ipo.id,
        gmp_date=date(2026, 11, 8),
        gmp_value=20.0,
        gmp_percent=20.0,
        issue_price=ipo.issue_price,
        lot_size=ipo.lot_size,
        source="ipo_guru",
    )
    prediction.expected_listing_price = 120.0
    prediction.expected_profit = 2000.0
    prediction.expected_return = 20.0

    payload = build_listing_result_payload(
        ipo_id=ipo.id,
        prediction_id="prediction-501",
        ipo=ipo,
        prediction=prediction,
    )

    assert payload["direction_accuracy"] is False
    assert payload["actual_gain_percent"] == -10.0


def test_ipo_service_evaluates_listing_outcome_against_the_saved_prediction():
    ipo = IPO(
        id="IP-502",
        name="Service IPO",
        issue_price=100.0,
        lot_size=200,
        actual_listing_price=115.0,
    )
    prediction = PredictionRecord(
        ipo_id=ipo.id,
        gmp_date=date(2026, 11, 8),
        gmp_value=10.0,
        gmp_percent=10.0,
        issue_price=ipo.issue_price,
        lot_size=ipo.lot_size,
        source="ipo_guru",
    )
    prediction.expected_listing_price = 110.0
    prediction.expected_profit = 2000.0
    prediction.expected_return = 10.0

    result = IPOService.evaluate_listing_result(ipo, prediction)

    assert result.predicted_listing_price == 110.0
    assert result.actual_listing_price == 115.0
    assert result.prediction_error == 5.0
    assert result.direction_accuracy is True


def test_listing_accuracy_handles_zero_gain_and_zero_prediction_denominator():
    ipo = IPO(
        id="IP-504",
        name="Zero Gain IPO",
        issue_price=100.0,
        actual_listing_price=100.0,
    )
    prediction = IPOService.create_prediction(
        ipo,
        GMPObservation(ipo_id=ipo.id, date=date(2026, 9, 24), gmp=0.0, gmp_percent=0.0),
    )

    result = IPOService.evaluate_listing_result(ipo, prediction)
    assert result.prediction_error == 0.0
    assert result.percentage_error == 0.0
    assert result.direction_accuracy is True

    prediction.expected_listing_price = 0.0
    result = IPOService.evaluate_listing_result(ipo, prediction)
    assert result.percentage_error is None


def test_listing_accuracy_rejects_missing_actual_listing_price():
    ipo = IPO(id="IP-505", name="Missing Outcome IPO", issue_price=100.0)
    prediction = PredictionRecord(
        ipo_id=ipo.id,
        gmp_date=date(2026, 9, 24),
        gmp_value=10.0,
        gmp_percent=10.0,
        issue_price=100.0,
        lot_size=1,
    )

    with pytest.raises(ValueError, match="actual_listing_price is required"):
        IPOService.evaluate_listing_result(ipo, prediction)


def test_listing_accuracy_rejects_nonpositive_issue_price():
    ipo = IPO(
        id="IP-506",
        name="Invalid Issue Price IPO",
        issue_price=0.0,
        actual_listing_price=100.0,
    )
    prediction = PredictionRecord(
        ipo_id=ipo.id,
        gmp_date=date(2026, 9, 24),
        gmp_value=10.0,
        gmp_percent=10.0,
        issue_price=0.0,
        lot_size=1,
    )
    prediction.expected_listing_price = 10.0
    prediction.expected_profit = 10.0
    prediction.expected_return = 0.0

    with pytest.raises(ValueError, match="issue_price must be positive"):
        IPOService.evaluate_listing_result(ipo, prediction)


def test_reconciliation_scores_each_pre_listing_prediction(monkeypatch, capsys):
    class Settings:
        ipo_api_key = "test-api-key"
        supabase_url = "https://example.supabase.co"
        supabase_key = "test-supabase-key"

    class Client:
        def __init__(self, api_key):
            assert api_key == "test-api-key"

        def fetch_ipo_detail(self, slug):
            assert slug == "example-ipo"
            return {
                "data": {
                    "name": "Example IPO",
                    "slug": slug,
                    "listing_date": "2026-09-25",
                    "actual_listing_price": "125",
                }
            }

    class Repository:
        def __init__(self):
            self.updated_listing = None
            self.results = []

        def get_ipo_records_for_reconciliation(self):
            return [{
                "ipo_id": "ipo-a",
                "ipo_name": "Example IPO",
                "ipo_slug": "example-ipo",
                "listing_date": "2026-09-25",
            }]

        def get_predictions_for_ipo(self, ipo_id):
            assert ipo_id == "ipo-a"
            return [
                {
                    "prediction_id": "prediction-before-1",
                    "ipo_id": ipo_id,
                    "gmp_date": "2026-09-20",
                    "gmp_value": 20.0,
                    "gmp_percent": 20.0,
                    "issue_price": 100.0,
                    "lot_size": 10,
                    "expected_listing_price": 120.0,
                    "expected_profit": 200.0,
                    "expected_return": 20.0,
                    "source": "ipo_guru",
                },
                {
                    "prediction_id": "prediction-before-2",
                    "ipo_id": ipo_id,
                    "gmp_date": "2026-09-24",
                    "gmp_value": 30.0,
                    "gmp_percent": 30.0,
                    "issue_price": 100.0,
                    "lot_size": 10,
                    "expected_listing_price": 130.0,
                    "expected_profit": 300.0,
                    "expected_return": 30.0,
                    "source": "ipo_guru",
                },
                {
                    "prediction_id": "prediction-on-listing-day",
                    "ipo_id": ipo_id,
                    "gmp_date": "2026-09-25",
                    "gmp_value": 40.0,
                    "gmp_percent": 40.0,
                    "issue_price": 100.0,
                    "lot_size": 10,
                    "expected_listing_price": 140.0,
                    "expected_profit": 400.0,
                    "expected_return": 40.0,
                    "source": "ipo_guru",
                },
            ]

        def update_listing_data(self, ipo_id, listing_date, listing_price):
            self.updated_listing = (ipo_id, listing_date, listing_price)

        def upsert_listing_result(self, ipo_id, prediction_id, ipo, prediction):
            self.results.append((prediction_id, ipo, prediction))
            return f"result-{prediction_id}"

    repository = Repository()
    monkeypatch.setattr(reconcile_listings.Settings, "from_env", lambda: Settings())
    monkeypatch.setattr(reconcile_listings, "IPOGuruClient", Client)
    monkeypatch.setattr(
        reconcile_listings.SupabaseRepository,
        "from_settings",
        lambda _settings: repository,
    )

    assert reconcile_listings.main() == 0

    assert repository.updated_listing == ("ipo-a", "2026-09-25", 125.0)
    assert [row[0] for row in repository.results] == [
        "prediction-before-1",
        "prediction-before-2",
    ]
    assert [row[1].actual_listing_price for row in repository.results] == [125.0, 125.0]
    assert "Prediction outcomes stored: 2" in capsys.readouterr().out


def test_reconciliation_skips_detail_without_actual_listing_price():
    class Client:
        def fetch_ipo_detail(self, _slug):
            return {"data": {"listing_date": "2026-09-25", "status": "listed"}}

    class Repository:
        def get_ipo_records_for_reconciliation(self):
            return [{
                "ipo_id": "ipo-a",
                "ipo_name": "Example IPO",
                "ipo_slug": "example-ipo",
                "listing_date": "2026-09-25",
            }]

        def get_predictions_for_ipo(self, _ipo_id):
            return [{"prediction_id": "prediction-a"}]

        def update_listing_data(self, *_args):
            pytest.fail("incomplete listing detail must not update the IPO")

        def upsert_listing_result(self, *_args):
            pytest.fail("incomplete listing detail must not create an outcome")

    assert reconcile_listings.reconcile_listings(Client(), Repository()) == (0, 0)


def test_reconciliation_skips_unlisted_ipo_without_detail_request():
    class Client:
        def fetch_ipo_detail(self, _slug):
            pytest.fail("future IPOs must not use a detail API request")

    class Repository:
        def get_ipo_records_for_reconciliation(self):
            return [{
                "ipo_id": "ipo-future",
                "ipo_name": "Future IPO",
                "ipo_slug": "future-ipo",
                "listing_date": (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)).isoformat(),
            }]

        def get_predictions_for_ipo(self, _ipo_id):
            return [{"prediction_id": "prediction-future"}]

        def update_listing_data(self, *_args):
            pytest.fail("future IPO must not be updated")

        def upsert_listing_result(self, *_args):
            pytest.fail("future IPO must not create an outcome")

    assert reconcile_listings.reconcile_listings(Client(), Repository()) == (0, 0)
