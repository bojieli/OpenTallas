#!/usr/bin/env python3
"""KV-405 10-24: R8 input for plan v3.9 = the kv44 bind's bus groups (bound on v3.8x; after r8_fault_exempt.py +
r8_invariant_split.py) rebased onto the new plan's latency (tools/die_plan/r8.py rebase: each member's bound depth moves
by its lane's cycle change, bind_latency.json plan_cycles -> the new plan's Plan.lane_latency).  The rebased groups are
written out so the landing table's bus_groups_digest matches the file G0 reads (r8/bus_groups.json).  The real table
comes from the re-bind on v3.9; this one prices the landing pads of the new lane depths.
    r8_rebase.py PLAN.json BUS_GROUPS_IN.json BIND_LATENCY.json OUT.json"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools/die_plan"))
import gen     # noqa: E402
import r8      # noqa: E402
import schema as S   # noqa: E402



def load(p):
    return json.loads((gzip.open(p, "rt") if str(p).endswith(".gz") else open(p)).read())


plan, bg_in, bl, out = sys.argv[1:5]
bg = load(bg_in)
bg, st = r8.rebase(bg, load(bl), gen.latency_table(S.Plan(S.load(plan))))
bg["note"] = bg.get("note", "") + f" | KV-405 r8_rebase onto {Path(plan).name}: {json.dumps(st)}"
bg["rebase"] = dict(bind_latency=Path(bl).name, **st)
Path(out).write_text(json.dumps(bg, indent=0) + "\n")
print(f"r8_rebase: {json.dumps(st)}")
