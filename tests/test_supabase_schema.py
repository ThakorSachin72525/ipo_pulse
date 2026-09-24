from pathlib import Path


SCHEMA_PATH = Path("supabase/migrations/001_initial_schema.sql")


def test_schema_uses_owned_ipo_uuid_and_required_columns():
    schema = SCHEMA_PATH.read_text()

    assert "ipo_id uuid primary key default gen_random_uuid()" in schema
    assert "ipo_name text not null" in schema
    assert "listing_price numeric(12, 2)" in schema
    assert "actual_listing_price" not in schema
    assert "create table if not exists public.ipo_gmp_history" in schema


def test_gmp_history_is_append_only_and_timestamp_unique():
    schema = SCHEMA_PATH.read_text()

    assert "gmp_history_id uuid primary key default gen_random_uuid()" in schema
    assert "ipo_id uuid not null references public.ipos(ipo_id) on delete cascade" in schema
    assert "observation_at timestamptz not null" in schema
    assert "unique (ipo_id, observation_at, source)" in schema
    assert "idx_ipo_gmp_history_ipo_observation" in schema
    assert "observed_date" not in schema


def test_schema_keeps_rls_enabled_without_public_policies():
    schema = SCHEMA_PATH.read_text()

    assert "alter table public.ipos enable row level security" in schema
    assert "alter table public.ipo_gmp_history enable row level security" in schema
    assert "create policy" not in schema.lower()