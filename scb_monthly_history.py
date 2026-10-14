"""Public monthly aggregate snapshots and sparse change log.

No individual business/workplace identifiers; never store per-CFAR history here.
Same-month runs replace the month's aggregate snapshot. Only actual changes
relative to the preceding monthly snapshot appear in the sparse change log.
"""
from pathlib import Path
import json

ROOT = Path("docs/data")
HISTORY = ROOT / "history"
VARIABLES = ("anstKl", "aeStat", "sniAvdelning", "reklamSparrTyp")

def put_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def update_history(summary):
    month = summary["fetched_at"][:7]
    if len(month) != 7 or month[4] != "-":
        raise ValueError("Invalid month")
    current = {
        "month": month,
        "municipality": "2580",
        "workplace_count": summary["workplace_count"],
        "categorical_distributions": summary["categorical_distributions"],
        "source": "SCB, allmänna företagsregistret – egen bearbetning"
    }
    put_json(HISTORY / (month + ".json"), current)
    snapshots = []
    for file in sorted(HISTORY.glob("????-??.json")):
        item = json.loads(file.read_text(encoding="utf-8"))
        if item.get("municipality") != "2580" or "categorical_distributions" not in item:
            raise ValueError("Unexpected snapshot format")
        snapshots.append(item)
    events = []
    previous = None
    for item in snapshots:
        if previous is None:
            events.append({"month": item["month"], "kind": "baseline",
                           "note": "Första observerade månaden; inga tidigare förändringar kan härledas."})
        else:
            if previous["workplace_count"] != item["workplace_count"]:
                events.append({"month": item["month"], "variable": "workplace_count",
                               "previous": previous["workplace_count"], "current": item["workplace_count"]})
            for variable in VARIABLES:
                prior = previous["categorical_distributions"].get(variable, {})
                now = item["categorical_distributions"].get(variable, {})
                for category in sorted(set(prior) | set(now)):
                    old = prior.get(category, 0)
                    new = now.get(category, 0)
                    if old != new:
                        events.append({"month": item["month"], "variable": variable,
                                       "category": category, "previous": old, "current": new})
        previous = item
    put_json(ROOT / "scb_monthly_changes.json", {
        "municipality": "2580",
        "grain": "monthly_aggregate",
        "months_observed": [s["month"] for s in snapshots],
        "events": events,
        "semantics": "Inga förändringshändelser betyder oförändrat aggregerat värde jämfört med föregående observerade månad. Mellan saknade månader går det inte att dra slutsatser.",
        "privacy": "Ingen individhistorik eller identifierande poster lagras."
    })
    print(f"Monthly history updated: {len(snapshots)} snapshots, {len(events)} sparse aggregate changes")
