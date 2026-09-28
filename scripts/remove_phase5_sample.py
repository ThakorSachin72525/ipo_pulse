"""Delete only the synthetic Phase 5 sample IPO and its cascading records."""

from __future__ import annotations

from supabase import create_client

from app.config import Settings


SAMPLE_SOURCE = "ipo_pulse_phase5_sample"


def main() -> int:
    settings = Settings.from_env()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    client = create_client(settings.supabase_url, settings.supabase_key)
    tagged_ipos = (
        client.table("ipos")
        .select("ipo_id,ipo_name")
        .eq("source", SAMPLE_SOURCE)
        .execute()
        .data
        or []
    )
    if not tagged_ipos:
        print("No Phase 5 sample IPO rows found; no changes made.")
        return 0

    deleted = (
        client.table("ipos")
        .delete()
        .eq("source", SAMPLE_SOURCE)
        .select("ipo_id")
        .execute()
        .data
        or []
    )
    if len(deleted) != len(tagged_ipos):
        raise RuntimeError(
            f"Expected to delete {len(tagged_ipos)} tagged IPO rows, deleted {len(deleted)}"
        )

    print(f"Deleted {len(deleted)} Phase 5 sample IPO row(s).")
    print("Related GMP, prediction, and listing-result rows are removed by foreign-key cascades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
