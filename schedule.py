"""Log GitHub Actions schedule events with their observed UTC and IST times."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


def main() -> int:
    now_utc = datetime.now(timezone.utc)
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = {}
    if event_path and Path(event_path).is_file():
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))

    print("GitHub Actions schedule diagnostic")
    print(f"event_name={os.environ.get('GITHUB_EVENT_NAME', 'local')}")
    print(f"schedule={event.get('schedule', os.environ.get('EXPECTED_CRON', 'not available'))}")
    print(f"run_id={os.environ.get('GITHUB_RUN_ID', 'local')}")
    print(f"run_attempt={os.environ.get('GITHUB_RUN_ATTEMPT', 'local')}")
    print(f"observed_utc={now_utc.isoformat(timespec='seconds')}")
    print(f"observed_ist={now_utc.astimezone(IST).isoformat(timespec='seconds')}")
    print(f"ref={os.environ.get('GITHUB_REF', 'local')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
