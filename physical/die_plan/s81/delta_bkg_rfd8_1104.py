#!/usr/bin/env python3
"""S81 plan event, bk_g view (DIE-S81-56/IQKV 11-04): the plan row of dsdv_bk_g in bk_sel__t2 named a stale 10-29 LEF and no liberty, so gen stops with
"macros have LEF but no timing liberty".  Row now names the signed RF-D form 8 view (re-signed flow-20261104-k-s81, odb 449a3779): LEF, TT lib, and the
clk[0] core tap at the signed insertion.  Outline, origin, pins_file, tap xy, reset tree unchanged.  bk_sel__t2 only.
    python3 delta_bkg_rfd8_1104.py PLAN_IN PLAN_OUT      (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
from plan_event_1104 import plan_text

M, TN, INST = "dsdv_bk_g", "bk_sel__t2", "u_bk_sel.u_sel.u_g"
VIEW = f"physical/die_plan/s81/cores/views/bk_g_rfd8_1104/{M}"
src, out = sys.argv[1:]
P = json.loads(Path(src).read_text())
assert [n for n, ty in P["partition_types"].items() for q in ty.get("hard_cores") or [] if q.get("module") == M] == [TN]
t = P["partition_types"][TN]
c = next(c for c in t["hard_cores"] if c["inst"] == INST)
assert c["module"] == M and "lib" not in c and c["outline_um"] == [216.0, 172.8]
ins = json.loads(Path(f"{VIEW}/insertion.json").read_text())
c.update(lef=f"{VIEW}/{M}.lef", lib=f"{VIEW}/{M}_tt.lib")
tap = next(x for x in t["clock"]["taps"] if x["name"] == INST + ".clk[0]")
old = [tap["insertion_ps"], tap["insertion_ff_ps"]]
tap.update(insertion_ps=ins["tt"]["boundary"]["mean"], insertion_ff_ps=ins["ff"]["boundary"]["mean"],
           budget_owner=f"parent_budget pin_register_mean {VIEW}/insertion.json")
Path(out).write_text(plan_text(P))
print(json.dumps(dict(old_tap=old, tap=[tap["insertion_ps"], tap["insertion_ff_ps"]])))
