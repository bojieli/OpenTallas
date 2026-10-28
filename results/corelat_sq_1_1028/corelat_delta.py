#!/usr/bin/env python3
"""CORELAT-SQ-1: per partition type core-tap delta (plan INPUT for the die owner; this script never writes a plan).

From TABLE.json (corelat_table.py) and PLAN: for every partition type with hard cores, list each core clock pin with
  current plan tap (insertion_ps / insertion_ff_ps / budget_owner) and the NEW tap:
  early (TT mean > common): kind core, name inst.pin, xy at the transformed LEF clock pin (early_core_taps rule),
  insertion_ps = TT mean, insertion_ff_ps = FF mean, budget_owner 'SIGNED ...' | 'parent_budget ...';
  not early: no core tap (grid/common), and any current early tap on it is listed under 'drop'.
usage: corelat_delta.py TABLE.json PLAN ROOT OUT.json
"""
import json, sys, collections
from pathlib import Path

T, PLAN, ROOT, OUT = sys.argv[1:5]
sys.path.insert(0, str(Path(ROOT) / "tools/die_plan"))
import cores as C  # noqa: E402

tab = json.load(open(T)); p = json.load(open(PLAN))
cnt = collections.Counter(x["type"] for x in p["partitions"])
bym = {r["module"]: r for r in tab["rows"]}
out = dict(table=T, plan=PLAN, plan_sha=tab["plan_sha"], types={}, summary=collections.Counter())

def pin_xy(c, pin):
    try:
        g = C.lef_pins(C.resolve(c["lef"], ROOT), c.get("module"))
    except Exception:  # noqa: BLE001
        return None
    pp = g.get(pin) or g.get(pin.split("[")[0])
    if not pp or not pp.get("xy"):
        return None
    x, y = c["origin_um"]; w, h = c["outline_um"]; px, py = pp["xy"]; o = c.get("orient", "R0")
    if o in ("MY", "R180"): px = w - px
    if o in ("MX", "R180"): py = h - py
    dx, dy = c.get("track_offset_um", [0., 0.])
    return [round(x + dx + px, 3), round(y + dy + py, 3)]

for tn, t in p["partition_types"].items():
    if not cnt[tn] or not t.get("hard_cores"):
        continue
    cur = {tp["name"]: tp for tp in (t.get("clock", {}) or {}).get("taps", []) or [] if tp.get("kind") == "core"}
    rows = []
    for c in t["hard_cores"]:
        r = bym.get(c["module"])
        if r is None:
            continue
        pins = [(q["pin"], q) for q in r["per_pin"]] if r.get("per_pin") else [(None, r)]
        for pin, q in pins:
            pname = pin or ((r.get("view_measure") or {}).get("pins") or ["ck"])[0]
            name = f"{c['inst']}.{pname}"
            old = cur.get(name) or next((v for k, v in cur.items() if k.startswith(c["inst"] + ".")), None) if not pin else cur.get(name)
            tap = q.get("tap")
            row = dict(inst=c["inst"], module=c["module"], pin=pname, name=name, placements=cnt[tn],
                       current=dict(insertion_ps=old.get("insertion_ps"), insertion_ff_ps=old.get("insertion_ff_ps"),
                                    budget_owner=(old.get("budget_owner") or "")[:100]) if old else None,
                       source=r.get("source"), label=r.get("label"))
            if not tap:
                row["action"] = "NO NUMBER (keep plan tap; see table)"; out["summary"]["no_number"] += cnt[tn]
            elif tap["early"]:
                row["action"] = "EARLY TAP" + (" (re-tap)" if old and old.get("insertion_ps") not in (None, 250, 250.0) else " (new)")
                row["new"] = dict(name=name, kind="core", xy=(old or {}).get("xy") or pin_xy(c, pname) or "TO-DO: transformed clock pin of the bound view (plan core has no LEF / pin not parsed)",
                                  insertion_ps=tap["insertion_ps"], insertion_ff_ps=tap["insertion_ff_ps"],
                                  budget_owner=tap["budget_owner"][:300], early_tt_ps=tap["early_tt_ps"], early_ff_ps=tap["early_ff_ps"],
                                  note="CORELAT-SQ-1: early core tap (12.3 v5.0) at the placed view's boundary-register mean")
                out["summary"]["early_" + ("signed" if tap["budget_owner"].startswith("SIGNED") else "parent_budget")] += cnt[tn]
            else:
                if tap.get("within_band"): row["within_band_tt_ps"] = round(tap["insertion_ps"] - 250, 1)
                row["action"] = "DROP early tap -> common" if old and (old.get("insertion_ps") or 250) > 250 else "no tap (common)"
                out["summary"]["drop" if row["action"].startswith("DROP") else "common"] += cnt[tn]
            rows.append(row)
    out["types"][tn] = dict(count=cnt[tn], core_taps_early=any(x.get("new") for x in rows),
                            all_signed=all(x.get("new", {}).get("budget_owner", "SIGNED").startswith("SIGNED") for x in rows if x.get("new")),
                            rows=rows)
json.dump(out, open(OUT, "w"), indent=1)
print(OUT, dict(out["summary"]), "types", len(out["types"]))
