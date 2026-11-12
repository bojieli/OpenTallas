#!/usr/bin/env python3
"""resign_list.py R12B_DIR DIEREVIEW_TSV LFCS_DEPTHS_JSON OUT.tsv [SHIP_PLAN] [STAGES]: one ready12b-A re-sign list, a column per reason.

Reasons: diereview (resign_batch_ready12b.tsv decision), lfcs_depth (leaf CS_*_D stage = kit RTL params change),
lfcs_direct (B1), tapwin (B2), band (B3), reachfix2 (B4).  Value = 1 or the detail string."""
import csv
import json
import os
import re
import sys

R, DRT, LCD, OUT = sys.argv[1:5]
SHIP = sys.argv[5] if len(sys.argv) > 5 else os.path.join(R, "plan_ready12b_A.json")
STAGES = (sys.argv[6] if len(sys.argv) > 6 else "lfcs_direct,band,reachfix2").split(",")
rows = {}


def mark(t, col, v="1"):
    rows.setdefault(t, {})[col] = v


for r in csv.DictReader(open(DRT), delimiter="\t"):
    mark(r["type"], "diereview", r.get("decision") or "1")
for t in json.load(open(LCD)):
    mark(t, "lfcs_depth")
for col, f in [x for x in (("lfcs_direct", "r1_lfcs.json"), ("band", "r3_band.json"), ("reachfix2", "r4_rf2.json")) if x[0] in STAGES]:
    for t in json.load(open(os.path.join(R, f)))["types_changed"]:
        mark(t, col)
for ln in open(os.path.join(R, "s2_tapwin.log")):
    m = re.match(r"W (\S+?)\.(clk\S*) (\S+) -> (\S+)", ln)
    if m:
        t = m.group(1)
        old = rows.get(t, {}).get("tapwin", "")
        mark(t, "tapwin", (old + ";" if old else "") + "%s:%s->%s" % m.group(2, 3, 4))
pre = [ln for ln in open(os.path.join(R, "s2_tapwin.log")) if ln.startswith("P ") or "per_type" in ln]
for ln in pre:
    m = re.search(r"(phy__t\d+)", ln)
    if m:
        mark(m.group(1), "tapwin", rows.get(m.group(1), {}).get("tapwin") or "per_type")
# reachfix2_fc: lanes whose fixed_cycles the re-priced REACH-FIX-2 changed (base -> composed), src + dst types
B0 = json.load(open("/srv/opentallas-scratch2/claude/s87bind/plan_ready12ng.json"))
P = json.load(open(SHIP))
pm = {p["name"]: p["type"] for p in P["partitions"]}
topo = {b["lane"]: b for b in json.load(open("/srv/opentallas-scratch2/claude/s81-leaf-floor-2/out_lfcs/bind_latency.json"))["buses"]
        if b.get("lane")}
fb = {x["id"]: x.get("fixed_cycles") for x in B0["lanes"]}
fc_lanes = []
for x in P["lanes"]:
    if x.get("fixed_cycles") != fb.get(x["id"]):
        fc_lanes.append([x["id"], fb.get(x["id"]), x.get("fixed_cycles")])
        t = topo.get(x["id"])
        for pn in ((t["src"], t["dst"]) if t else ()):
            old = rows.get(pm[pn], {}).get("reachfix2_fc", "")
            mark(pm[pn], "reachfix2_fc", (old + ";" if old else "") + "%s:%s->%s" % (x["id"], fb.get(x["id"]), x.get("fixed_cycles")))
json.dump(fc_lanes, open(os.path.join(R, "fc_lanes.json"), "w"), indent=1)
print("fixed_cycles lanes changed", len(fc_lanes))
cols = ["diereview", "lfcs_depth", "lfcs_direct", "tapwin", "band", "reachfix2", "reachfix2_fc"]
with open(OUT, "w") as f:
    f.write("type\tn_reasons\t" + "\t".join(cols) + "\n")
    for t in sorted(rows):
        d = rows[t]
        f.write("%s\t%d\t%s\n" % (t, len(d), "\t".join(d.get(c, "") for c in cols)))
print("types", len(rows), {c: sum(1 for d in rows.values() if c in d) for c in cols})
