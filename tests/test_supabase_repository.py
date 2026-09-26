from datetime import datetime, timezone

import pytest

from app.repositories.supabase_repository import (
    SupabaseRepository,
    build_gmp_payload,
    build_ipo_payload,
)


def test_build_ipo_payload_does_not_use_external_id():
    payload = build_ipo_payload(
        {
            "id": "external-slug",
            "name": "Example IPO",
            "issue_price": 100.0,
            "source": "ipo_guru",
        }
    )

    assert payload == {
        "ipo_name": "Example IPO",
        "issue_price": 100.0,
        "source": "ipo_guru",
    }
    assert "id" not in payload


def test_build_ipo_payload_maps_external_field_names():
    payload = build_ipo_payload(
        {
            "name": "Example IPO",
            "type": "mainboard",
            "actual_listing_price": 125.0,
        }
    )

    assert payload["ipo_name"] == "Example IPO"
    assert payload["ipo_type"] == "mainboard"
    assert payload["listing_price"] == 125.0


def test_build_ipo_payload_preserves_provider_slug_for_detail_lookup():
    payload = build_ipo_payload(
        {"name": "Example IPO", "slug": "example-ipo", "source": "ipo_guru"}
    )

    assert payload["ipo_slug"] == "example-ipo"


def test_repository_returns_all_prediction_snapshots_for_an_ipo():
    class Query:
        def __init__(self):
            self.predicates = []

        def select(self, columns):
            assert columns == "*"
            return self

        def eq(self, column, value):
            self.predicates.append((column, value))
            return self

        def order(self, column, desc):
            self.predicates.append((column, desc))
            return self

        def execute(self):
            return type("Response", (), {"data": [
                {"prediction_id": "p1", "gmp_date": "2026-09-24"},
                {"prediction_id": "p2", "gmp_date": "2026-09-25"},
            ]})()

    query = Query()

    class Client:
        def table(self, name):
            assert name == "ipo_predictions"
            return query

    predictions = SupabaseRepository(Client()).get_predictions_for_ipo("ipo-a")

    assert [row["prediction_id"] for row in predictions] == ["p1", "p2"]
    assert ("ipo_id", "ipo-a") in query.predicates
    assert ("gmp_date", False) in query.predicates


def test_repository_lists_provider_records_for_reconciliation():
    class Query:
        def __init__(self):
            self.source = None

        def select(self, columns):
            assert "ipo_slug" in columns
            return self

        def eq(self, column, value):
            self.source = (column, value)
            return self

        def execute(self):
            assert self.source == ("source", "ipo_guru")
            return type("Response", (), {"data": [{"ipo_slug": "example-ipo"}]})()

    query = Query()

    class Client:
        def table(self, name):
            assert name == "ipos"
            return query

    assert SupabaseRepository(Client()).get_ipo_records_for_reconciliation() == [
        {"ipo_slug": "example-ipo"}
    ]


def test_verify_schema_checks_for_slug_migration():
    selections = []

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, columns):
            selections.append((self.table_name, columns))
            return self

        def limit(self, _count):
            return self

        def execute(self):
            return type("Response", (), {"data": []})()

    class Client:
        def table(self, name):
            return Query(name)

    repository = SupabaseRepository(Client())

    assert repository.verify_schema() == (
        "ipos",
        "ipo_gmp_history",
        "ipo_predictions",
        "ipo_listing_results",
    )
    assert ("ipos", "ipo_slug") in selections


def test_dashboard_data_filters_samples_and_joins_ipo_names():
    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def order(self, _column, desc):
            assert desc is False
            return self

        def execute(self):
            if self.table_name == "ipos":
                return type("Response", (), {"data": [
                    {"ipo_id": "ipo-a", "ipo_name": "Alpha IPO", "source": "ipo_guru"},
                    {"ipo_id": "sample-a", "ipo_name": "Sample IPO", "source": "sample"},
                ]})()
            if self.table_name == "ipo_gmp_history":
                return type("Response", (), {"data": [
                    {"ipo_id": "ipo-a", "gmp": 20.0},
                    {"ipo_id": "sample-a", "gmp": 15.0},
                ]})()
            if self.table_name == "ipo_predictions":
                return type("Response", (), {"data": [{
                    "ipo_id": "ipo-a", "expected_listing_price": 120.0,
                }]})()
            return type("Response", (), {"data": [{
                "ipo_id": "ipo-a", "actual_listing_price": 118.0,
            }]})()

    class Client:
        def table(self, table_name):
            return Query(table_name)

    data = SupabaseRepository(Client()).get_dashboard_data()

    assert [row["ipo_name"] for row in data["ipos"]] == ["Alpha IPO"]
    assert data["gmp_history"] == [{"name": "Alpha IPO", "ipo_id": "ipo-a", "gmp": 20.0}]
    assert data["predictions"][0]["name"] == "Alpha IPO"
    assert data["results"][0]["actual_listing_price"] == 118.0


def test_build_gmp_payload_normalizes_timestamp_to_utc():
    payload = build_gmp_payload(
        "owned-uuid",
        datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc),
        {"gmp": 48.0, "gmp_percent": 24.0, "estimated_listing_price": 148.0},
    )

    assert payload["observation_at"] == "2026-09-25T14:00:00+00:00"
    assert payload["gmp"] == 48.0


def test_build_gmp_payload_rejects_local_timestamp():
    with pytest.raises(ValueError, match="timezone"):
        build_gmp_payload("owned-uuid", datetime(2026, 9, 25, 14, 0), {})