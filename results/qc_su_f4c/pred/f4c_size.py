#!/usr/bin/env python3
"""QC-SU-F4C: 12.8 d1 plan-computed per-stage driver sizing of an f4_g4c spec, with the GATING predictor uf_phys3 v1
(OT_PHYS_FIT) on the PLANNED leg layers (--layers m56: tree legs on PG-via-free M5 V / M6 H, the F4B/F4C feed plan;
m45: the uf_phys default).  Wraps su_branch_size.size() unchanged (fixed BUFx8..x24 list, coordinate descent, slew
cap, cells only: no site / stage / wire change), then re-predicts the sized spec with f4b_pred3 (same predictor call).
Deterministic, no measured input; values frozen with the plan.  PLAN MODEL, UNCHECKED.
usage: f4c_size.py REPO SPEC.tcl GEO LIBDIR OUT.tcl --layers m56|m45 [--passes N]"""
import json, os, sys, tempfile
from pathlib import Path
R = Path(sys.argv[1]); spec, geo, libdir, out = sys.argv[2:6]
lay = sys.argv[sys.argv.index("--layers") + 1]
passes = int(sys.argv[sys.argv.index("--passes") + 1]) if "--passes" in sys.argv else 3
assert os.environ.get("OT_PHYS_FIT"), "OT_PHYS_FIT (uf_phys3 v1) required"
sys.path.insert(0, str(R / "results/qc_su_prog_l1_1026"))
import phys_gate as PG
import su_branch_size as SB
U = PG.U
if lay == "m56":
    U.R45 = 0.5 * (1.89935e-2 + 1.18796e-2) * U.KR; U.C45 = 0.5 * (1.64264e-1 + 1.87426e-1) * U.KC
P0 = U.Plan(spec, geo, {})
seg = {n: U.man(v["xy"], P0.nodes[v["par"]]["xy"]) for n, v in P0.nodes.items() if v["par"]}
tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(dict(seg_um=seg), tf); tf.close()
r = SB.size(spec, tf.name, geo, libdir, passes)
SB.write_spec(spec, r["cells"], out, "QC-SU-F4C per-stage sizing (12.8 d1, plan-computed by uf_phys3 v1 on %s legs before build; "
              "cells only, sites/stages unchanged) of %s" % (lay, Path(spec).name))
r["layers"] = lay; r["fit"] = os.environ["OT_PHYS_FIT"]
r["provenance"] = dict(argv=[sys.executable] + list(sys.argv), sha256={p: PG.sha(p) for p in (spec, geo, __file__, SB.__file__, PG.__file__, out, os.environ["OT_PHYS_FIT"])})
Path(str(Path(out).with_suffix("")) + ".size.json").write_text(json.dumps(r, indent=1))
print("SIZED", lay, json.dumps(dict(before=r["before"], after=r["after"], n_changes=len(r["changes"]))))
