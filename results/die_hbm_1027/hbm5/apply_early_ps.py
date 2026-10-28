#!/usr/bin/env python3
"""DIE-HBM-5 hook for HBM-CORE-LAT-2 (COORD 02:5x): core taps keep insertion 250 / 202.5 ps until the early_ps table lands.
Every one of the 733 core taps carries budget_owner = the hard-core module, which is the join key.
TABLE json: {"<module>": {"tt_ps": float, "ff_ps": float, "source": "ETM|real|CTS-est"}}; modules not in the table keep
250/202.5. An empty table is a no-op (prints the census).  usage: apply_early_ps.py PLAN_IN TABLE [PLAN_OUT]"""
import json, sys, hashlib, pathlib, collections
pin = pathlib.Path(sys.argv[1]); tab = json.loads(pathlib.Path(sys.argv[2]).read_text()) if sys.argv[2] != "-" else {}
P = json.loads(pin.read_text()); hit = collections.Counter(); miss = collections.Counter()
for tn, t in P["partition_types"].items():
    for tp in t.get("clock", {}).get("taps", []):
        if tp.get("kind") != "core": continue
        m = tp.get("budget_owner"); r = tab.get(m)
        if r is None: miss[m] += 1; continue
        tp["insertion_ps"], tp["insertion_ff_ps"] = float(r["tt_ps"]), float(r["ff_ps"])
        tp["note"] = tp.get("note", "") + " | HBM-CORE-LAT-2 early_ps (%s)" % r.get("source", "?"); hit[m] += 1
print("taps set", sum(hit.values()), "modules", len(hit), "| kept 250/202.5:", sum(miss.values()), "taps,", len(miss), "modules")
if len(sys.argv) > 3:
    out = pathlib.Path(sys.argv[3]); txt = json.dumps(P, indent=1); out.write_text(txt)
    (out.parent / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
