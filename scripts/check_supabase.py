"""Verify Supabase access and required tables without writing data."""

from __future__ import annotations

from app.config import Settings
from app.repositories.supabase_repository import SupabaseRepository


def main() -> int:
    tables = SupabaseRepository.from_settings(Settings.from_env()).verify_schema()
    print("Supabase connection verified")
    print("Tables verified: " + ", ".join(tables))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())