#!/usr/bin/env python3
"""KV-TIMING-FORMS-1: NEW wrapper = bound OLD wrapper + the plan's reset.port_relays only (reset_port_relays.apply).
usage: mk_relay_bench.py PLAN TYPE BOUND.sv OUT.sv [--mutant deep_bout]"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/kvtf1/repo/tools/die_plan")
import reset_port_relays
a = sys.argv[1:]
mut = None
if "--mutant" in a:
    i = a.index("--mutant"); mut = a[i + 1]; del a[i:i + 2]
plan, tn, bound, out = a
t = json.loads(Path(plan).read_text())["partition_types"][tn]
rows = t["reset"].get("port_relays", [])
base = [r for r in rows if r["name"] == "hrst"]
txt = Path(bound).read_text()
# the bound vF text may already contain the hrst row's relays; apply only rows whose relays are not yet emitted
rows = [r for r in rows if f"u_prl_{r['name']}_0" not in txt]
if mut == "deep_bout":      # an observed epoch released 8 clocks late
    rows = rows + [dict(name="mut", depth=8, sinks=["u_bout_o_phy_Q__sN_fhN"])]
    # remove that sink from any row that already has it
    for r in rows[:-1]:
        r["sinks"] = [s for s in r["sinks"] if s != "u_bout_o_phy_Q__sN_fhN"]
    rows = [r for r in rows if r["sinks"]]
new, rec = reset_port_relays.apply(txt, rows)
mod = re.search(r"^module\s+(\w+)", new, re.M)[1]
new = re.sub(rf"^module\s+{mod}\b", f"module {mod}_new", new, count=1, flags=re.M)
Path(out).write_text(new)
print(json.dumps(dict(type=tn, mutant=mut, rows=len(rows), relays=sum(r['depth'] for r in rows), sinks=sum(len(r['sinks']) for r in rows))))
