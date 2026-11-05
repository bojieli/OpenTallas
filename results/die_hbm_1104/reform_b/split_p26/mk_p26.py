#!/usr/bin/env python3
"""HBM-REFORM-B4 d44v part 26 pre: slot ot_hbm_svc_sm_group_rel_id 776.304x646.92 -> 768.96x639.36, origin kept: mk_split tile edges need the 8.64 lattice."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1]); D = json.loads((pd / "die_plan.json").read_text()); n = 0
for ty in D["partition_types"].values():
    for h in ty.get("hard_cores") or []:
        if h["module"] == "ot_hbm_svc_sm_group_rel_id":
            assert abs(h["outline_um"][0] - 776.304) < 1e-3 and abs(h["outline_um"][1] - 646.92) < 1e-3; h["outline_um"] = [768.96, 639.36]; n += 1
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n"); print("part 26 pre rows", n)
