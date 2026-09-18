#!/usr/bin/env python3
"""
Run one validation pass over the Workday customer invoices.

    python3 validator/validate.py                 # read ../api from disk, write results there
    python3 validator/validate.py --base-url https://<you>.github.io/<repo>   # read a hosted copy
    python3 validator/validate.py --only DRAFT    # skip invoices already approved
    python3 validator/validate.py --check         # also grade against api/workday/expected-results.json

Outputs (all under api/validation-runs/):
    latest.json        the current run — what the Workday UI and the monitor page read
    history.json       the last 168 run summaries (a week of hourly runs)
    runs/<run_id>.json the full run, kept for audit

The scheduler (validator/scheduler.py or .github/workflows/hourly-validation.yml)
calls this once an hour.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import Context, validate_invoice  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "api")
OUT = os.path.join(API, "validation-runs")

ENDPOINTS = {
    "invoices": "workday/customer-invoices.json",
    "customers": "workday/customers.json",
    "revenue_categories": "workday/revenue-categories.json",
    "rules": "workday/exception-rules.json",
    "poms": "poms/orders.json",
    "nga": "trackers/nga-tracker.json",
    "factoring": "trackers/factoring-tracker.json",
    "dk_tracker": "trackers/dk21-sharepoint-tracker.json",
    "ey": "ey/final-invoices.json",
    "salesforce": "salesforce/accounts.json",
    "expected": "workday/expected-results.json",
}


def load(path: str, base_url: str | None):
    if base_url:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/{path}", timeout=30) as r:
            return json.load(r)
    with open(os.path.join(API, path), encoding="utf-8") as f:
        return json.load(f)


def build_context(src: dict) -> Context:
    ctx = Context()
    ctx.customers = {c["customer_id"]: c for c in src["customers"]["data"]}
    ctx.revenue_categories = {r["revenue_category"]: r for r in src["revenue_categories"]["data"]}
    ctx.rules = {r["rule_id"]: r for r in src["rules"]["data"]}
    ctx.poms = {o["order_number"]: o for o in src["poms"]["data"]}
    ctx.nga = {t["invoice_number"]: t for t in src["nga"]["data"]}
    ctx.factoring = {p["payment_id"]: p for p in src["factoring"]["data"]}
    ctx.dk_tracker = {t["poms_order_number"]: t for t in src["dk_tracker"]["data"]}
    ctx.ey = {e["workday_invoice_number"]: e for e in src["ey"]["data"]}
    ctx.salesforce = {a["workday_customer_id"]: a for a in src["salesforce"]["data"]}
    return ctx


def run(base_url: str | None, only_status: str | None, check: bool, interval_minutes: int = 60) -> dict:
    started = datetime.now(timezone.utc).replace(microsecond=0)
    src = {k: load(v, base_url) for k, v in ENDPOINTS.items()}
    ctx = build_context(src)

    headers = src["invoices"]["data"]
    if only_status:
        headers = [h for h in headers if h["status"] == only_status]
    results = []
    for h in headers:
        detail = load(f"workday/customer-invoices/{h['invoice_number']}.json", base_url)["data"]
        results.append(validate_invoice(detail, ctx))

    by_status = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "HOLD")}
    by_company = {}
    for r in results:
        c = by_company.setdefault(r["company"], {"PASS": 0, "FAIL": 0, "HOLD": 0, "invoices": 0})
        c[r["status"]] += 1
        c["invoices"] += 1
    by_rule = {}
    for r in results:
        for f in r["findings"]:
            if f["outcome"] == "INFO":
                continue
            e = by_rule.setdefault(f["rule_id"], {"rule_id": f["rule_id"], "name": ctx.rules.get(f["rule_id"], {}).get("name"),
                                                  "severity": f["severity"], "hits": 0, "invoices": set()})
            e["hits"] += 1
            e["invoices"].add(r["invoice_number"])
    for e in by_rule.values():
        e["invoices"] = sorted(e["invoices"])

    finished = datetime.now(timezone.utc).replace(microsecond=0)
    run_id = started.strftime("run-%Y%m%dT%H%MZ")
    payload = {
        "run_id": run_id, "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": finished.isoformat().replace("+00:00", "Z"),
        "duration_seconds": (finished - started).total_seconds(),
        "schedule": {"interval_minutes": interval_minutes,
                     "next_run_at": (started + timedelta(minutes=interval_minutes)).isoformat().replace("+00:00", "Z"),
                     "trigger": os.environ.get("VALIDATION_TRIGGER", "manual")},
        "source": base_url or "local api/", "scope": only_status or "all statuses",
        "invoices_checked": len(results), "summary": by_status, "by_company": by_company,
        "by_rule": sorted(by_rule.values(), key=lambda e: -e["hits"]),
        "results": results,
    }

    if check:
        exp = {e["invoice_number"]: e for e in src["expected"]["data"]}
        grade = []
        for r in results:
            e = exp.get(r["invoice_number"])
            if not e:
                continue
            ok_status = e["expected_status"] == r["status"]
            ok_rules = sorted(e["expected_findings"]) == r["rules_failed"]
            grade.append({"invoice_number": r["invoice_number"], "expected": e["expected_status"], "actual": r["status"],
                          "expected_rules": sorted(e["expected_findings"]), "actual_rules": r["rules_failed"],
                          "match": ok_status and ok_rules, "scenario": e["scenario"]})
        payload["answer_key_check"] = {"graded": len(grade), "matched": sum(1 for g in grade if g["match"]),
                                       "mismatches": [g for g in grade if not g["match"]]}
    return payload


def write(payload: dict) -> None:
    os.makedirs(os.path.join(OUT, "runs"), exist_ok=True)
    with open(os.path.join(OUT, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "runs", f"{payload['run_id']}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    hist_path = os.path.join(OUT, "history.json")
    history = []
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            history = json.load(f).get("runs", [])
    history = [h for h in history if h["run_id"] != payload["run_id"]]
    history.append({"run_id": payload["run_id"], "started_at": payload["started_at"], "invoices_checked": payload["invoices_checked"],
                    "summary": payload["summary"], "trigger": payload["schedule"]["trigger"]})
    history = history[-168:]
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump({"runs": history, "count": len(history)}, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("VALIDATION_BASE_URL"))
    ap.add_argument("--only", default=None, help="only invoices with this Workday status, e.g. DRAFT")
    ap.add_argument("--check", action="store_true", help="grade against the answer key")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    payload = run(a.base_url, a.only, a.check, a.interval)
    write(payload)
    s = payload["summary"]
    print(f"{payload['run_id']}: {payload['invoices_checked']} invoices — PASS {s['PASS']}, FAIL {s['FAIL']}, HOLD {s['HOLD']}")
    for c, v in payload["by_company"].items():
        print(f"  {c}: {v['invoices']} invoices — PASS {v['PASS']}, FAIL {v['FAIL']}, HOLD {v['HOLD']}")
    if "answer_key_check" in payload:
        k = payload["answer_key_check"]
        print(f"answer key: {k['matched']}/{k['graded']} matched")
        for m in k["mismatches"]:
            print("  MISMATCH", m["invoice_number"], m["expected"], m["expected_rules"], "->", m["actual"], m["actual_rules"])
    print(f"next run: {payload['schedule']['next_run_at']}")


if __name__ == "__main__":
    main()
