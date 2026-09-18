#!/usr/bin/env python3
"""
Hourly scheduler for the validation run. Standard library only.

    python3 validator/scheduler.py                   # run now, then at the top of every hour
    python3 validator/scheduler.py --interval 15     # every 15 minutes (demo pace)
    python3 validator/scheduler.py --once            # one run and exit (same as validate.py)

For the GitHub Pages deployment the equivalent is .github/workflows/hourly-validation.yml,
which runs validate.py on a cron and commits api/validation-runs/ so the hosted
Workday UI and monitor page pick up the new results on the next page load.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate  # noqa: E402


def next_boundary(interval: int) -> datetime:
    now = datetime.now(timezone.utc)
    minute = (now.minute // interval + 1) * interval
    return (now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minute))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="minutes between runs (default 60)")
    ap.add_argument("--base-url", default=os.environ.get("VALIDATION_BASE_URL"))
    ap.add_argument("--only", default=None)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()

    os.environ["VALIDATION_TRIGGER"] = "scheduler"
    while True:
        payload = validate.run(a.base_url, a.only, check=False, interval_minutes=a.interval)
        validate.write(payload)
        s = payload["summary"]
        print(f"[{payload['started_at']}] {payload['run_id']}: {payload['invoices_checked']} invoices — "
              f"PASS {s['PASS']}  FAIL {s['FAIL']}  HOLD {s['HOLD']}", flush=True)
        if a.once:
            break
        nxt = next_boundary(a.interval)
        print(f"  next run at {nxt.isoformat()}", flush=True)
        time.sleep(max(1.0, (nxt - datetime.now(timezone.utc)).total_seconds()))


if __name__ == "__main__":
    main()
