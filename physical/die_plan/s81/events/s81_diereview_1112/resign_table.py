#!/usr/bin/env python3
"""S81 ready12b hand-floorplan: signed-type re-plan / batch re-sign table.

Inputs: window report (signed_excluded_input, signed_would_change,
REGION_TREE_BALANCE, name_only_signed_written) + DIEREVIEW type_table.
Rule (OWNER 11-12 04:37): signed types are NOT fixed; re-plan wherever it
helps die closure, list for one batch re-sign.  Leaf types belong to
S81-LEAF-FLOOR-1 (listed, decision deferred to that lane)."""
import json, sys, csv

wr = json.load(open(sys.argv[1]))
tt = json.load(open(sys.argv[2]))
out = sys.argv[3]

def base(t):
    return t.split("__pv")[0]

types = {}
for r in tt:
    types.setdefault(r["type"], r)

def find(t):
    if t in types:
        return types[t]
    c = [r for k, r in types.items() if k.startswith(t + "__") or base(k) == t]
    return c[0] if c else None

signed = list(dict.fromkeys(wr["signed_excluded_input"] + list(wr["signed_would_change"])))
rtb = wr.get("REGION_TREE_BALANCE", {})
rows = []
for t in signed:
    r = find(t) or {}
    fam = r.get("family", "?")
    wc = wr["signed_would_change"].get(t, {})
    deficits = [p["need"] - p["effective"] for p in wc.values()]
    hard = [p for p, v in rtb.get(t, {}).items() if "HARD" in v.get("kind", "")]
    hops = r.get("hops_over_405", 0) or 0
    maxhop = r.get("max_hop", 0) or 0
    changes, why = [], []
    if t.startswith("ot_s81sl_leaf") or t.startswith("ot_s81sl_kv_leaf"):
        dec = "DEFER S81-LEAF-FLOOR-1"
        changes.append("leaf re-floor (core re-pack/rotate in slot or new slot) by S81-LEAF-FLOOR-1")
        why.append("leaf reach/street family owned by LEAF-FLOOR-1")
    else:
        dec = "KEEP"
    if wc:
        changes.append(f"write {len(wc)} port windows (need-eff max {max(deficits)} ps)")
        why.append("window = measured need; unwritten windows leave die STA on stale budgets")
        dec = "RESIGN" if dec == "KEEP" else dec
    if hard:
        changes.append(f"early clock landing for {len(hard)} HARD ports (need>cap)")
        why.append("REGION_TREE_BALANCE: cap cannot meet need; structural landing, not window")
        dec = "RESIGN" if dec == "KEEP" else dec
    if hops and not dec.startswith("DEFER"):
        changes.append(f"internal reg re-place: {hops} hops >405 um (max {maxhop:.0f})")
        why.append("reach >405 um fails die/landed timing by construction")
        dec = "RESIGN"
    rows.append(dict(type=t, family=fam, decision=dec,
                     win_ports=len(wc), win_max_deficit_ps=max(deficits) if deficits else 0,
                     rtb_hard_ports=len(hard), hops_over_405=hops,
                     max_hop_um=round(maxhop, 1), core_fill=round(r.get("core_fill", 0) or 0, 3),
                     plan_change="; ".join(changes) or "none",
                     why_die_closure="; ".join(why) or "no die-level problem measured"))

HOLD = ("svc_hi_dsdv_svc_rs", "svc_lo_dsdv_svc_rs", "svc_hi_dsdv_svc_pvso_entry", "bk_sel__t2")
for r in rows:
    r["hold"] = "HOLD(brief: svc_rs/pvso_entry/bk_sel__t2)" if r["type"].startswith(HOLD) else ""
seen = {r["type"] for r in rows}
for t in wr.get("name_only_signed_written", []):
    if t in seen:
        continue
    r = find(t) or {}
    leaf = t.startswith(("ot_s81sl_leaf", "ot_s81sl_kv_leaf"))
    rows.append(dict(type=t, family=r.get("family", "?"),
                     decision="DEFER S81-LEAF-FLOOR-1" if leaf else "RESIGN",
                     win_ports=-1, win_max_deficit_ps=0, rtb_hard_ports=0,
                     hops_over_405=r.get("hops_over_405", 0) or 0,
                     max_hop_um=round(r.get("max_hop", 0) or 0, 1),
                     core_fill=round(r.get("core_fill", 0) or 0, 3),
                     plan_change="windows already written in ready12w (name-only signed)",
                     why_die_closure="SDC/windows differ from the signed run -> re-sign to count",
                     hold=""))

with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), Counter(r["decision"] for r in rows))
for r in rows:
    print(f'{r["decision"]:22s} {r["type"]:42s} {r["family"]:22s} win={r["win_ports"]:3d}/{r["win_max_deficit_ps"]:3d} rtbH={r["rtb_hard_ports"]} hops={r["hops_over_405"]}')
