#!/usr/bin/env python3
"""DIE-QC-77 11-05: extended to every QC type with forwarded ring inputs (ring-input hold class, -105..-266 ps on 22 rows).
Based on DIE-QC-74 11-05 (coll_ft added; DIE-QC-70 11-04 form): QC stm/coll_ftm/coll_ft ring writers on the falling fclk edge (hold class of FLOW-30's 07:34 table).
clock.ring_hold write_fall_types = stm bases + coll_ftm; landing_ring_wreg on every ring input of those types (writer
start registered, K + 1 at bind).  Idempotent.  usage: delta_ring_fall.py PLAN [OUT]; needs tools/die_plan on sys.path"""
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["tools/die_plan"]
import landing_contract as LC
import schema as S

path = sys.argv[1]
text = open(path).read()
plan = json.loads(text)
seps = next(sp for sp in ((", ", ": "), (",", ":")) if json.dumps(plan, separators=sp) + "\n" == text)
P = S.Plan(S.load(path), Path(path).resolve())
plan["clock"]["ring_hold"] = {"sender_ps": -85, "write_edge": "fall", "write_fall_types": [], "ft_ring_max_ps": 350}
done = {}
for tn in sorted({p["type"] for p in P.parts.values()}):
    if LC.ring_input_ports(P, tn):
        buses = sorted({re.sub(r"^fclk_in_", "", ck) for ck, _ in LC.ring_input_ports(P, tn)})
        assert buses, tn
        plan["partition_types"][tn].setdefault("clock", {})["landing_ring_wreg"] = {"buses": buses, "dsrep": 1}
        done[tn] = len(buses)
plan["clock"]["ring_hold"]["write_fall_types"] = sorted({t.split("__")[0] for t in done})
out = sys.argv[2] if len(sys.argv) > 2 else path
open(out, "w").write(json.dumps(plan, separators=seps) + "\n")
print(len(done), "types", done)
