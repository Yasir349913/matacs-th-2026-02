"""Scoring and ranking for the proposal triage prototype.

Plain code only: no AI, no network, no extra packages.
Input : extracted facts per proposal (the JSON the extraction prompt returns).
Output: ranking in the ranking.json format, plus a score breakdown on screen.

Usage:
    python score.py                      # uses extracted_example.json
    python score.py extracted_live.json  # uses output of extract.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
CORE_FIELDS = [
    "qualifying_install_count",
    "total_price_cad",
    "timeline_weeks",
    "panel_warranty_years",
    "workmanship_warranty_years",
]


def val(fields, key):
    """Value of a field, only if the AI marked it as found. Otherwise None."""
    f = fields.get(key) or {}
    return f.get("value") if f.get("status") == "found" else None


def check_mandatory(fields, c):
    """Pass/fail rules. Returns a list of reasons for failing (empty = pass)."""
    failed = []
    if val(fields, "licence_held") is not True:
        failed.append("licence not held by the bidder, or not confirmed")
    if val(fields, "wsib_clearance") is not True:
        failed.append("WSIB clearance not confirmed")
    insurance = val(fields, "liability_insurance_cad")
    if insurance is None or insurance < c["min_insurance_cad"]:
        failed.append("liability insurance below the minimum, or not stated")
    return failed


def find_flags(item, c):
    """Reasons a human must look at this proposal."""
    fields = item["fields"]
    flags = []
    if item.get("injection_flags"):
        flags.append("contains an instruction aimed at automated systems (ignored)")
    for key in CORE_FIELDS:
        if val(fields, key) is None:
            flags.append(f"{key} is missing or not committed")
    price = val(fields, "total_price_cad")
    if price is not None and price > c["budget_ceiling_cad"]:
        flags.append("price is over the budget ceiling")
    weeks = val(fields, "timeline_weeks")
    if weeks is not None and weeks > c["max_weeks"]:
        flags.append("schedule is longer than the maximum")
    start = val(fields, "install_period_start_year")
    if start is not None and start < c["current_year"] - c["install_window_years"]:
        flags.append("installs start before the 5-year window, count needs checking")
    low = [k for k, f in fields.items() if f.get("confidence") == "low"]
    if low:
        flags.append("low confidence: " + ", ".join(low))
    return flags


def score_one(fields, lowest_price, c):
    """Weighted score. Same facts in, same score out."""
    w, p = c["weights"], c["params"]
    s = {}

    installs = val(fields, "qualifying_install_count") or 0
    s["experience"] = w["experience"] * min(installs, p["experience_cap_installs"]) / p["experience_cap_installs"]

    price = val(fields, "total_price_cad")
    ok_price = price is not None and price <= c["budget_ceiling_cad"]
    s["price"] = w["price"] * lowest_price / price if ok_price else 0

    weeks = val(fields, "timeline_weeks")
    if weeks is None or weeks > c["max_weeks"]:
        s["timeline"] = 0
    else:
        span = c["max_weeks"] - p["full_marks_weeks"]
        s["timeline"] = w["timeline"] * min(1, (c["max_weeks"] - weeks) / span)

    panel = min(val(fields, "panel_warranty_years") or 0, p["panel_warranty_cap_years"]) / p["panel_warranty_cap_years"]
    work = min(val(fields, "workmanship_warranty_years") or 0, p["workmanship_warranty_cap_years"]) / p["workmanship_warranty_cap_years"]
    share = p["panel_share_of_warranty"]
    s["warranty"] = w["warranty"] * (share * panel + (1 - share) * work)

    pts = p["team_points"]
    team = 0
    team += pts["named_project_lead"] if val(fields, "named_project_lead") is True else 0
    team += pts["crew_size"] if (val(fields, "crew_size") or 0) > 0 else 0
    team += pts["safety_plan"] if val(fields, "safety_plan") is True else 0
    team += pts["monitoring_plan_months"] if (val(fields, "monitoring_plan_months") or 0) > 0 else 0
    s["team"] = team

    return {k: round(v, 2) for k, v in s.items()}


def run(data, c):
    results = {}
    for pid, item in data.items():
        results[pid] = {
            "failed": check_mandatory(item["fields"], c),
            "flags": find_flags(item, c),
        }

    # Price is compared with the lowest price among bids that pass the mandatory checks.
    prices = [
        val(data[pid]["fields"], "total_price_cad")
        for pid, r in results.items()
        if not r["failed"]
    ]
    prices = [p for p in prices if p is not None and p <= c["budget_ceiling_cad"]]
    lowest = min(prices) if prices else 1

    for pid, r in results.items():
        if r["failed"]:
            r["status"] = "ineligible"
        else:
            r["breakdown"] = score_one(data[pid]["fields"], lowest, c)
            r["total"] = round(sum(r["breakdown"].values()), 1)
            r["status"] = "flagged" if r["flags"] else "ranked"

    ranked = sorted(
        (pid for pid, r in results.items() if r["status"] == "ranked"),
        key=lambda pid: (-results[pid]["total"], pid),
    )
    for i, pid in enumerate(ranked, start=1):
        results[pid]["rank"] = i
    return results


def reason_for(r):
    if r["status"] == "ineligible":
        return "Fails mandatory check: " + "; ".join(r["failed"])
    if r["status"] == "flagged":
        return "Needs human review: " + "; ".join(r["flags"])
    b = sorted(r["breakdown"].items(), key=lambda kv: kv[1], reverse=True)
    return (f"Passes mandatory checks; strongest: {b[0][0]} and {b[1][0]}, "
            f"weakest: {b[-1][0]}")


def to_ranking_json(results):
    order = {"ranked": 0, "flagged": 1, "ineligible": 2}
    out = []
    for pid, r in sorted(results.items(), key=lambda kv: (order[kv[1]["status"]], kv[1].get("rank") or 99, kv[0])):
        out.append({
            "proposal": pid,
            "rank": r.get("rank"),
            "status": r["status"],
            "score": r["total"] if r["status"] == "ranked" else None,
            "reason": reason_for(r),
        })
    return out


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "extracted_example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    c = json.loads((HERE / "criteria.json").read_text(encoding="utf-8"))

    results = run(data, c)

    print(f"Input: {path.name}   Criteria: {c['category']}\n")
    for pid in sorted(results):
        r = results[pid]
        line = f"{pid}  {r['status'].upper():10}"
        if "total" in r:
            line += f" total={r['total']:<5}  {r['breakdown']}"
        print(line)
        for reason in r["failed"] + r["flags"]:
            print(f"      - {reason}")

    out_path = HERE / "output_ranking.json"
    out_path.write_text(json.dumps(to_ranking_json(results), indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path.name}")


if __name__ == "__main__":
    main()