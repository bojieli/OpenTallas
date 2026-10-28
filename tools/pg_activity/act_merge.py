#!/usr/bin/env python3
"""PG-ACTIVITY-4: merge per-case act_SM.txt files (name rate) from vcd_activity.py.
  act_merge.py OUTDIR CASEDIR...   each CASEDIR has act_SM.txt + activity_summary.json (cycles)
Writes OUTDIR/act_SM_mean.txt (cycle-weighted mean over all case windows), OUTDIR/act_SM_peak.txt (= the case with the
largest summed rate) and OUTDIR/cases.json (per case: cycles, summed rate, bits)."""
import json, os, sys
from collections import defaultdict
out, dirs = sys.argv[1], sys.argv[2:]
os.makedirs(out, exist_ok=True)
tot = defaultdict(float); W = 0; rows = []
for d in dirs:
    s = json.load(open(os.path.join(d, "activity_summary.json")))
    cyc = s.get("cycles") or s.get("clock_cycles") or s.get("nck")
    assert cyc, ("no cycle count in", d, list(s))
    r = {}
    for ln in open(os.path.join(d, "act_SM.txt")):
        p = ln.split()
        if len(p) == 2: r[p[0]] = float(p[1])
    for k, v in r.items(): tot[k] += v * cyc
    W += cyc
    rows.append({"case": d, "cycles": cyc, "sum_rate": round(sum(r.values()), 3), "bits": len(r)})
with open(os.path.join(out, "act_SM_mean.txt"), "w") as f:
    for k in sorted(tot): f.write("%s %.6f\n" % (k, tot[k] / W))
pk = max(rows, key=lambda x: x["sum_rate"])
os.system("cp %s %s" % (os.path.join(pk["case"], "act_SM.txt"), os.path.join(out, "act_SM_peak.txt")))
json.dump({"cases": rows, "peak_case": pk["case"], "mean_cycles": W}, open(os.path.join(out, "cases.json"), "w"), indent=1)
print(json.dumps({"peak": pk, "n": len(rows), "cycles": W}))
