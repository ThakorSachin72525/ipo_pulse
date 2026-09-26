"""Supabase persistence for IPO metadata and GMP observations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.config import Settings
from app.models.ipo_model import GMPObservation, IPO, ListingResult, PredictionRecord


IPO_COLUMNS = (
    "ipo_name",
    "issue_price",
    "lot_size",
    "price_band",
    "ipo_type",
    "status",
    "open_date",
    "close_date",
    "allotment_date",
    "refund_date",
    "demat_date",
    "listing_date",
    "listing_price",
    "issue_size",
    "face_value",
    "minimum_investment",
    "subscription_total",
    "ipo_slug",
    "source",
    "source_updated_at",
)


def build_ipo_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Select API fields that match the `ipos` table."""
    payload = {column: record.get(column) for column in IPO_COLUMNS}
    payload["ipo_name"] = record.get("ipo_name", record.get("name"))
    payload["ipo_type"] = record.get("ipo_type", record.get("type"))
    payload["ipo_slug"] = record.get("ipo_slug", record.get("slug"))
    payload["listing_price"] = record.get("listing_price", record.get("actual_listing_price"))
    payload["source"] = record.get("source", "ipo_guru")
    if not payload["ipo_name"]:
        raise ValueError("IPO name is required")
    return {key: value for key, value in payload.items() if value is not None}


def build_gmp_payload(
    ipo_id: str,
    observation_at: datetime,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Build a UTC GMP observation payload for idempotent insertion."""
    if observation_at.tzinfo is None or observation_at.utcoffset() is None:
        raise ValueError("observation_at must include a timezone")
    observed_utc = observation_at.astimezone(timezone.utc).isoformat()
    return {
        "ipo_id": ipo_id,
        "observation_at": observed_utc,
        "gmp": record.get("gmp"),
        "gmp_percent": record.get("gmp_percent"),
        "estimated_listing_price": record.get("estimated_listing_price"),
        "source": record.get("source", "ipo_guru"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def build_prediction_payload(
    ipo_id: str,
    gmp_history_id: str,
    ipo: IPO,
    gmp: GMPObservation,
) -> dict[str, Any]:
    """Serialize a GMP-backed prediction for storage or downstream evaluation."""
    prediction = PredictionRecord.from_gmp(ipo=ipo, gmp_observation=gmp)
    return {
        "ipo_id": ipo_id,
        "gmp_history_id": gmp_history_id,
        "gmp_value": prediction.gmp_value,
        "gmp_percent": prediction.gmp_percent,
        "issue_price": prediction.issue_price,
        "lot_size": prediction.lot_size,
        "expected_listing_price": prediction.expected_listing_price,
        "expected_profit": prediction.expected_profit,
        "expected_return": prediction.expected_return,
        "source": prediction.source,
        "gmp_date": gmp.date.isoformat(),
    }


def build_listing_result_payload(
    ipo_id: str,
    prediction_id: str,
    ipo: IPO,
    prediction: PredictionRecord,
) -> dict[str, Any]:
    """Serialize a prediction outcome for storage or reporting."""
    result = ListingResult.from_prediction(ipo=ipo, prediction=prediction)
    return {
        "ipo_id": ipo_id,
        "prediction_id": prediction_id,
        "actual_listing_price": result.actual_listing_price,
        "predicted_listing_price": result.predicted_listing_price,
        "actual_gain_percent": result.actual_gain_percent,
        "prediction_error": result.prediction_error,
        "percentage_error": result.percentage_error,
        "direction_accuracy": result.direction_accuracy,
    }


class SupabaseRepository:
    """Write IPO records and append-only GMP observations to Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "SupabaseRepository":
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        return cls(create_client(settings.supabase_url, settings.supabase_key))

    def find_ipo_id(self, ipo_name: str, source: str = "ipo_guru") -> str | None:
        response = (
            self._client.table("ipos")
            .select("ipo_id")
            .eq("ipo_name", ipo_name)
            .eq("source", source)
            .limit(1)
            .execute()
        )
        return response.data[0]["ipo_id"] if response.data else None

    def upsert_ipo(self, record: dict[str, Any]) -> str:
        payload = build_ipo_payload(record)
        existing_id = self.find_ipo_id(payload["ipo_name"], payload["source"])
        if existing_id:
            self._client.table("ipos").update(payload).eq("ipo_id", existing_id).execute()
            return existing_id

        response = self._client.table("ipos").insert(payload).execute()
        if not response.data:
            raise RuntimeError("Supabase did not return the inserted IPO")
        return response.data[0]["ipo_id"]

    def upsert_gmp_observation(
        self,
        ipo_id: str,
        observation_at: datetime,
        record: dict[str, Any],
    ) -> str:
        payload = build_gmp_payload(ipo_id, observation_at, record)
        response = (
            self._client.table("ipo_gmp_history")
            .upsert(payload, on_conflict="ipo_id,observation_at,source")
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the GMP observation")
        return response.data[0]["gmp_history_id"]

    def upsert_prediction(
        self,
        ipo_id: str,
        gmp_history_id: str,
        ipo: IPO,
        gmp: GMPObservation,
    ) -> str:
        payload = build_prediction_payload(ipo_id, gmp_history_id, ipo, gmp)
        response = (
            self._client.table("ipo_predictions")
            .upsert(payload, on_conflict="ipo_id,gmp_history_id,source")
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the prediction record")
        return response.data[0]["prediction_id"]

    def find_latest_prediction(self, ipo_id: str) -> dict[str, Any] | None:
        response = (
            self._client.table("ipo_predictions")
            .select("*")
            .eq("ipo_id", ipo_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_ipo_records_for_reconciliation(self) -> list[dict[str, Any]]:
        response = (
            self._client.table("ipos")
            .select("ipo_id,ipo_name,ipo_slug,issue_price,lot_size,listing_date,listing_price")
            .eq("source", "ipo_guru")
            .execute()
        )
        return response.data

    def get_predictions_for_ipo(self, ipo_id: str) -> list[dict[str, Any]]:
        response = (
            self._client.table("ipo_predictions")
            .select("*")
            .eq("ipo_id", ipo_id)
            .order("gmp_date", desc=False)
            .execute()
        )
        return response.data

    def update_listing_data(
        self,
        ipo_id: str,
        listing_date: str | None,
        listing_price: float,
    ) -> None:
        payload: dict[str, Any] = {"listing_price": listing_price}
        if listing_date:
            payload["listing_date"] = listing_date
        self._client.table("ipos").update(payload).eq("ipo_id", ipo_id).execute()

    def upsert_listing_result(
        self,
        ipo_id: str,
        prediction_id: str,
        ipo: IPO,
        prediction: PredictionRecord,
    ) -> str:
        payload = build_listing_result_payload(ipo_id, prediction_id, ipo, prediction)
        response = (
            self._client.table("ipo_listing_results")
            .upsert(payload, on_conflict="ipo_id,prediction_id")
            .execute()
        )
        if not response.data:
            raise RuntimeError("Supabase did not return the listing result")
        return response.data[0]["listing_result_id"]

    def get_daily_report_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ipos_response = self._client.table("ipos").select(
            "ipo_id,ipo_name,status,source"
        ).execute()
        ipo_names = {
            row["ipo_id"]: row["ipo_name"]
            for row in ipos_response.data
            if row.get("source") == "ipo_guru"
        }
        status_by_id = {
            row["ipo_id"]: row.get("status")
            for row in ipos_response.data
            if row.get("source") == "ipo_guru"
        }

        gmp_response = (
            self._client.table("ipo_gmp_history")
            .select("ipo_id,gmp,estimated_listing_price,observation_at")
            .order("observation_at", desc=True)
            .execute()
        )
        current_ipos = []
        seen_ipo_ids: set[str] = set()
        for row in gmp_response.data:
            ipo_id = row["ipo_id"]
            if ipo_id not in ipo_names or ipo_id in seen_ipo_ids:
                continue
            seen_ipo_ids.add(ipo_id)
            current_ipos.append(
                {
                    "name": ipo_names.get(ipo_id, "IPO"),
                    "status": status_by_id.get(ipo_id),
                    "gmp": row.get("gmp"),
                    "estimated_listing_price": row.get("estimated_listing_price"),
                }
            )

        results_response = (
            self._client.table("ipo_listing_results")
            .select("ipo_id,actual_listing_price,predicted_listing_price,percentage_error,direction_accuracy")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        recent_results = [
            {"name": ipo_names.get(row["ipo_id"], "IPO"), **row}
            for row in results_response.data
            if row["ipo_id"] in ipo_names
        ]
        return current_ipos, recent_results

    def verify_schema(self) -> tuple[str, ...]:
        """Run read-only queries against the required tables."""
        tables = ("ipos", "ipo_gmp_history", "ipo_predictions", "ipo_listing_results")
        for table in tables:
            self._client.table(table).select("*").limit(1).execute()
        self._client.table("ipos").select("ipo_slug").limit(1).execute()
        return tables
