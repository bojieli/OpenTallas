#!/usr/bin/env python3
"""HBM-REFORM-B5 + B4 d44v part 26 pre: slot ot_hbm_svc_sm_group_rel_id 776.304x646.92 -> 768.96x639.36, origin kept: mk_split tile edges need the 8.64 lattice."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1]); D = json.loads((pd / "die_plan.json").read_text()); n = 0
for ty in D["partition_types"].values():
    for h in ty.get("hard_cores") or []:
        if h["module"] == "ot_hbm_svc_sm_group_rel_id":
            assert abs(h["outline_um"][0] - 776.304) < 1e-3 and abs(h["outline_um"][1] - 646.92) < 1e-3; h["outline_um"] = [768.96, 639.36]; n += 1
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n"); print("part 26 pre rows", n)
# ot_wbq_root (part 25, DPL-0033 at the W seam, f25/k3): the macro columns start 4.32 from the seam face and the W-face flops pile into 3 slots. West margin 15.12, channels 11.016.
M = json.loads((pd / "core_macros.json").read_text()); c = M["cores"]["ot_wbq_root"]; XS = [15.12, 120.96, 226.8, 332.64]
for i, m in enumerate(c["macros"]):
    r = m["rect_um"]; w = r[2] - r[0]; x = XS[i % 4]; assert abs(w - 94.824) < 1e-6; m["rect_um"] = [x, r[1], round(x + w, 3), r[3]]
(pd / "core_macros.json").write_text(json.dumps(M, indent=1) + "\n"); print("root macros moved")
