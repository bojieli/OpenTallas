#!/usr/bin/env python3
"""part 37: recipes_b2 entries for the two ctl sub-cores + reset_contract modules.  recipes_p37.py REPO"""
import json, sys
from pathlib import Path
R = Path(sys.argv[1]); RD = "rtl/hbm_accel/cores_split/ot_hgi_sfu_core_split3/"
f = R / "physical/die_plan/hbm_arch_cores/recipes_b2.json"; d = json.loads(f.read_text())
SRC = ("HBM-FORM-TIMING-11 d44v part 37: sub-core of ot_hgi_sfu_core_split3__ctl (I205 delay-line cut of HBM-FORM-TIMING-10, "
       "0 cycles; lock-step bench + mutants results/die_hbm_1106/ctlsplit_p37/BENCH.txt)")
d["ot_hgi_sfu_split3_ctl_rest_1c"] = dict(defines=[], params={}, util=0.45, macros=[], functional_type="sfu_ctl",
    source=SRC + "; rest = ctl oneclk wrapper around ot_hgi_sfu_split3_ctl_rest_core + seam_d/seam_q",
    top="ot_hgi_sfu_split3_ctl_rest_1c", files=[RD + "ot_hgi_sfu_split3_ctl_rest_core.sv", RD + "ot_hgi_sfu_split3_ctl_rest_1c.sv"])
d["ot_hgi_sfu_split3_ctl_pipe_1c"] = dict(defines=[], params={}, util=0.45, macros=[], functional_type="sfu_ctl",
    source=SRC + "; pipe = 21,816 delay-line flops + a local copy of the ctl reset sync (rst_n -> 2 flops -> relay)",
    top="ot_hgi_sfu_split3_ctl_pipe_1c", files=[RD + "ot_hgi_sfu_split3_ctl_pipe_core.sv", RD + "ot_hgi_sfu_split3_ctl_pipe_1c.sv"])
f.write_text(json.dumps(d, indent=2) + "\n")
g = R / "physical/die_plan/hbm/reset_contract.json"; c = json.loads(g.read_text())
for m in ("ot_hgi_sfu_split3_ctl_pipe_1c", "ot_hgi_sfu_split3_ctl_rest_1c"):
    if m not in c["modules"]:
        c["modules"].append(m)
c["modules"] = sorted(c["modules"]) if c["modules"][:-2] == sorted(c["modules"][:-2]) else c["modules"]
g.write_text(json.dumps(c, indent=1) + "\n")
print("recipes + reset_contract updated")
