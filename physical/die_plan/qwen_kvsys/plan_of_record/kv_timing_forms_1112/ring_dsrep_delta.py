#!/usr/bin/env python3
"""KV-TIMING-FORMS-1 11-12: landing-ring read-select replication (clock.landing_ring_wreg.dsrep) for named KV types.
Same field vG changed for kv3_io_cor_v1 (1 -> 8; EQ diff vs vD = exactly this field; ot_dp_clk_landing_cas DSREP = same-D
read-select register copies, 0 data cycles).  usage: ring_dsrep_delta.py PLAN_IN PLAN_OUT TYPE=DSREP [TYPE=DSREP ...]
Fail closed: the type must already carry landing_ring_wreg (a type without it needs a bus list = separate decision),
DSREP must divide 64 (clock_landings.py), and the output may differ from the input only in those fields."""
import json, sys
from pathlib import Path
a, b, *rows = sys.argv[1:]
p = json.loads(Path(a).read_text())
q = json.loads(json.dumps(p))
ch = []
for r in rows:
    tn, n = r.split("="); n = int(n)
    assert 64 % n == 0, r
    w = q["partition_types"][tn]["clock"].get("landing_ring_wreg")
    assert w is not None, f"{tn}: no landing_ring_wreg (needs a bus list)"
    ch.append((tn, w["dsrep"], n)); w["dsrep"] = n
for tn in p["partition_types"]:
    x, y = p["partition_types"][tn], q["partition_types"][tn]
    if x != y:
        assert tn in dict((c[0], 1) for c in ch)
        assert {k: v for k, v in x["clock"].items() if k != "landing_ring_wreg"} == {k: v for k, v in y["clock"].items() if k != "landing_ring_wreg"}
        assert {k: v for k, v in x.items() if k != "clock"} == {k: v for k, v in y.items() if k != "clock"}
assert {k: v for k, v in p.items() if k != "partition_types"} == {k: v for k, v in q.items() if k != "partition_types"}
Path(b).write_text(json.dumps(q, indent=1) + "\n")
print(json.dumps(ch))
