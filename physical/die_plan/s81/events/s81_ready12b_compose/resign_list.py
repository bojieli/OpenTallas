#!/usr/bin/env python3
"""resign_list.py R12B_DIR DIEREVIEW_TSV LFCS_DEPTHS_JSON OUT.tsv: one ready12b-A re-sign list, a column per reason.

Reasons: diereview (resign_batch_ready12b.tsv decision), lfcs_depth (leaf CS_*_D stage = kit RTL params change),
lfcs_direct (B1), tapwin (B2), band (B3), reachfix2 (B4).  Value = 1 or the detail string."""
import csv
import json
import os
import re
import sys

R, DRT, LCD, OUT = sys.argv[1:5]
rows = {}


def mark(t, col, v="1"):
    rows.setdefault(t, {})[col] = v


for r in csv.DictReader(open(DRT), delimiter="\t"):
    mark(r["type"], "diereview", r.get("decision") or "1")
for t in json.load(open(LCD)):
    mark(t, "lfcs_depth")
for col, f in (("lfcs_direct", "r1_lfcs.json"), ("band", "r3_band.json"), ("reachfix2", "r4_rf2.json")):
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
nfs = os.path.join(R, "r4b_nfs_lanes.json")
if os.path.exists(nfs):
    P = json.load(open(os.path.join(R, "plan_ready12b_A.json")))
    pm = {p["name"]: p["type"] for p in P["partitions"]}
    for lane, src, dst, old, new in json.load(open(nfs))["lanes_changed"]:
        for pn in (src, dst):
            mark(pm[pn], "native_fixed_sync", "%s:%s->%s" % (lane, old, new))
cols = ["diereview", "lfcs_depth", "lfcs_direct", "tapwin", "band", "reachfix2", "native_fixed_sync"]
with open(OUT, "w") as f:
    f.write("type\tn_reasons\t" + "\t".join(cols) + "\n")
    for t in sorted(rows):
        d = rows[t]
        f.write("%s\t%d\t%s\n" % (t, len(d), "\t".join(d.get(c, "") for c in cols)))
print("types", len(rows), {c: sum(1 for d in rows.values() if c in d) for c in cols})
