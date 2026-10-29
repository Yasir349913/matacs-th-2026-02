
"""Scoring and ranking for the proposal triage prototype.

Plain code only: no AI, no network, no extra packages.
Input : extracted facts per proposal (the JSON the extraction prompt returns).
Output: ranking in the ranking.json format, plus a score breakdown on screen.

Usage:
    python score.py                      # uses extracted_example.json
    python score.py extracted_live.json  # uses output of extract.py
"""
import json
import math
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

BOOL_FIELDS = {
    "licence_held",
    "wsib_clearance",
    "named_project_lead",
    "safety_plan",
}

POSITIVE_FIELDS = {"total_price_cad", "timeline_weeks"}

NUMBER_FIELDS = {
    "liability_insurance_cad",
    "qualifying_install_count",
    "install_period_start_year",
    "total_price_cad",
    "timeline_weeks",
    "panel_warranty_years",
    "workmanship_warranty_years",
    "crew_size",
    "monitoring_plan_months",
}


def val(fields, key):
    """Return a validated value only when extraction marked it as found.

    Invalid types, booleans used as numbers, non-finite floats, negative
    numbers, and zero for positive-only fields are treated as missing.
    """
    f = fields.get(key)

    if not isinstance(f, dict) or f.get("status") != "found":
        return None

    v = f.get("value")

    if key in BOOL_FIELDS:
        return v if isinstance(v, bool) else None

    if key in NUMBER_FIELDS:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None

        # Reject NaN and positive/negative Infinity.
        if isinstance(v, float) and not math.isfinite(v):
            return None

        if v < 0:
            return None

        if key in POSITIVE_FIELDS and v == 0:
            return None

    return v


def check_mandatory(fields, c):
    """Return mandatory-check failures; an empty list means pass."""
    failed = []

    if val(fields, "licence_held") is not True:
        failed.append("licence not held by the bidder, or not confirmed")

    if val(fields, "wsib_clearance") is not True:
        failed.append("WSIB clearance not confirmed")

    insurance = val(fields, "liability_insurance_cad")

    if insurance is None or insurance < c["min_insurance_cad"]:
        failed.append(
            "liability insurance below the minimum, or not stated"
        )

    return failed


def find_flags(item, c):
    """Return reasons why a human should review this proposal."""
    fields = item["fields"]
    flags = []

    if item.get("injection_flags"):
        flags.append(
            "contains an instruction aimed at automated systems (ignored)"
        )

    for key in CORE_FIELDS:
        if val(fields, key) is None:
            flags.append(
                f"{key} is missing, invalid or not committed"
            )

    price = val(fields, "total_price_cad")

    if price is not None and price > c["budget_ceiling_cad"]:
        flags.append("price is over the budget ceiling")

    weeks = val(fields, "timeline_weeks")

    if weeks is not None and weeks > c["max_weeks"]:
        flags.append("schedule is longer than the maximum")

    start = val(fields, "install_period_start_year")

    if start is not None and start < (
        c["current_year"] - c["install_window_years"]
    ):
        flags.append(
            "installs start before the 5-year window, count needs checking"
        )

    for key in (BOOL_FIELDS | NUMBER_FIELDS) - set(CORE_FIELDS):
        f = fields.get(key)

        if (
            isinstance(f, dict)
            and f.get("status") == "found"
            and f.get("value") is not None
            and val(fields, key) is None
        ):
            flags.append(f"invalid value in {key}")

    low = [
        key
        for key, field in fields.items()
        if isinstance(field, dict) and field.get("confidence") == "low"
    ]

    if low:
        flags.append("low confidence: " + ", ".join(low))

    return flags


def score_one(fields, lowest_price, c):
    """Calculate the weighted score deterministically."""
    weights = c["weights"]
    params = c["params"]
    scores = {}

    installs = val(fields, "qualifying_install_count") or 0
    experience_cap = params["experience_cap_installs"]

    scores["experience"] = (
        weights["experience"]
        * min(installs, experience_cap)
        / experience_cap
    )

    price = val(fields, "total_price_cad")
    price_is_valid = (
        price is not None
        and price <= c["budget_ceiling_cad"]
    )

    scores["price"] = (
        weights["price"] * lowest_price / price
        if price_is_valid
        else 0
    )

    weeks = val(fields, "timeline_weeks")

    if weeks is None or weeks > c["max_weeks"]:
        scores["timeline"] = 0
    else:
        span = c["max_weeks"] - params["full_marks_weeks"]

        scores["timeline"] = (
            weights["timeline"]
            * min(1, (c["max_weeks"] - weeks) / span)
        )

    panel = (
        min(
            val(fields, "panel_warranty_years") or 0,
            params["panel_warranty_cap_years"],
        )
        / params["panel_warranty_cap_years"]
    )

    workmanship = (
        min(
            val(fields, "workmanship_warranty_years") or 0,
            params["workmanship_warranty_cap_years"],
        )
        / params["workmanship_warranty_cap_years"]
    )

    panel_share = params["panel_share_of_warranty"]

    scores["warranty"] = weights["warranty"] * (
        panel_share * panel
        + (1 - panel_share) * workmanship
    )

    team_points = params["team_points"]
    team_score = 0

    if val(fields, "named_project_lead") is True:
        team_score += team_points["named_project_lead"]

    if (val(fields, "crew_size") or 0) > 0:
        team_score += team_points["crew_size"]

    if val(fields, "safety_plan") is True:
        team_score += team_points["safety_plan"]

    if (val(fields, "monitoring_plan_months") or 0) > 0:
        team_score += team_points["monitoring_plan_months"]

    scores["team"] = team_score

    return {key: round(value, 2) for key, value in scores.items()}


def clean_item(item):
    """Return validated structure for fields and injection flags."""
    if not isinstance(item, dict) or not isinstance(
        item.get("fields"), dict
    ):
        return {}, []

    flags = item.get("injection_flags")

    return (
        item["fields"],
        flags if isinstance(flags, list) else [],
    )


def run(data, c):
    cleaned = {
        pid: clean_item(item)
        for pid, item in data.items()
    }

    results = {}

    for pid, (fields, injections) in cleaned.items():
        if not fields:
            results[pid] = {
                "failed": [],
                "status": "flagged",
                "flags": [
                    "no usable extraction, needs human review"
                ],
            }
            continue

        results[pid] = {
            "failed": check_mandatory(fields, c),
            "flags": find_flags(
                {
                    "fields": fields,
                    "injection_flags": injections,
                },
                c,
            ),
        }

    # Compare prices among bids that pass mandatory checks.
    prices = [
        val(cleaned[pid][0], "total_price_cad")
        for pid, result in results.items()
        if "status" not in result and not result["failed"]
    ]

    prices = [
        price
        for price in prices
        if price is not None
        and price <= c["budget_ceiling_cad"]
    ]

    lowest_price = min(prices) if prices else 1

    for pid, result in results.items():
        if "status" in result:
            continue

        if result["failed"]:
            result["status"] = "ineligible"
        else:
            result["breakdown"] = score_one(
                cleaned[pid][0],
                lowest_price,
                c,
            )

            result["total"] = round(
                sum(result["breakdown"].values()),
                1,
            )

            result["status"] = (
                "flagged" if result["flags"] else "ranked"
            )

    ranked = sorted(
        (
            pid
            for pid, result in results.items()
            if result["status"] == "ranked"
        ),
        key=lambda pid: (
            -results[pid]["total"],
            pid,
        ),
    )

    for rank, pid in enumerate(ranked, start=1):
        results[pid]["rank"] = rank

    return results


def reason_for(result):
    if result["status"] == "ineligible":
        return (
            "Fails mandatory check: "
            + "; ".join(result["failed"])
        )

    if result["status"] == "flagged":
        return (
            "Needs human review: "
            + "; ".join(result["flags"])
        )

    breakdown = sorted(
        result["breakdown"].items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return (
        f"Passes mandatory checks; strongest: "
        f"{breakdown[0][0]} and {breakdown[1][0]}, "
        f"weakest: {breakdown[-1][0]}"
    )


def to_ranking_json(results):
    """Convert results to the required ranking JSON structure."""
    order = {
        "ranked": 0,
        "flagged": 1,
        "ineligible": 2,
    }

    output = []

    for pid, result in sorted(
        results.items(),
        key=lambda item: (
            order[item[1]["status"]],
            item[1].get("rank") or 99,
            item[0],
        ),
    ):
        output.append(
            {
                "proposal": pid,
                "rank": result.get("rank"),
                "status": result["status"],
                "score": (
                    result["total"]
                    if result["status"] == "ranked"
                    else None
                ),
                "reason": reason_for(result),
            }
        )

    return output


def main():
    path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else HERE / "extracted_example.json"
    )

    data = json.loads(path.read_text(encoding="utf-8"))
    criteria = json.loads(
        (HERE / "criteria.json").read_text(encoding="utf-8")
    )

    results = run(data, criteria)

    print(
        f"Input: {path.name}   "
        f"Criteria: {criteria['category']}\n"
    )

    for pid in sorted(results):
        result = results[pid]
        line = f"{pid}  {result['status'].upper():10}"

        if "total" in result:
            line += (
                f" total={result['total']:<5}  "
                f"{result['breakdown']}"
            )

        print(line)

        for reason in result["failed"] + result["flags"]:
            print(f"      - {reason}")

    output_path = HERE / "output_ranking.json"

    output_path.write_text(
        json.dumps(to_ranking_json(results), indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nWrote {output_path.name}")


if __name__ == "__main__":
    main()
