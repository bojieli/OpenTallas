#!/usr/bin/env python3
"""rec17.py REPO SHA256: recipe + reset-contract rows of part 17 (copy-then-replace: repo tree is hard-linked)."""
import json, os, sys
from pathlib import Path
repo = Path(sys.argv[1]); sha = sys.argv[2]
f = repo / "physical/die_plan/hbm_arch_cores/recipes_b2.json"; R = json.loads(f.read_text())
L1, LP = "ot_hbm_su_pg_lane1_core", "ot_hbm_su_pg_lane1p_core"
new = "rtl/hbm_accel/cores_split/reform_1104a/lanes4/ot_hbm_su_pg_lane1p_core.sv"
r = json.loads(json.dumps(R[L1]))
r["top"] = LP; r["rename_top"] = LP + "__mc"
r["files"] = [x for x in r["files"] if not x.endswith(L1 + ".sv")] + [new]
r.pop("files_at", None)
r["source"] = "HBM-REFORM-A d44v part 17: lane1 text with the module renamed, lanes_plain tile 440.64 x 112.32 (lockstep receipt in results/die_hbm_1104/reform_a/part17)"
r["wrapper_by_pins_sha256"] = {sha: "physical/die_plan/hbm_arch_cores/wrappers/oneclk/" + LP + ".sv"}
R[LP] = r
t = f.with_suffix(".tmp"); t.write_text(json.dumps(R, indent=1) + "\n"); os.replace(t, f)
f = repo / "physical/die_plan/hbm/reset_contract.json"; C = json.loads(f.read_text()); m = C["modules"]
if LP not in m:
    m.append(LP); m.sort()
C["modules_basis"] = C["modules_basis"].rstrip() + " d44v part 17: lane1p as lane1 (same RTL text), reset pins from the same parent reset through wires only."
t = f.with_suffix(".tmp"); t.write_text(json.dumps(C, indent=1) + "\n"); os.replace(t, f)
print("recipe", LP, "files", len(r["files"]))
