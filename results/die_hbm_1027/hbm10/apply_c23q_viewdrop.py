"""DIE-HBM-10 C23q last step (same edit as c22v, DIE-HBM-10 12:36): q_hub_nw/ne u_xq_Q_p{0,1}_eg
(ot_hgi_sm_xload_xq_pegress) stop citing the stale 10-17 view physical/ref_tile/hgi_sm_xq_pegress (369.36x369.36,
clocks USE SIGNAL) for their 362.88x276.48 TRIAL outline -> lef/lib dropped = PENDING-VIEW until their own view is
signed off.  Outlines, origins, pins unchanged.  Chain: apply_c23q.py -> ft_corridor.py -> path_hbm_census_complete.py -> this.
usage: apply_c23q_viewdrop.py PLAN_DIR (in place)"""
import json, sys, hashlib
from pathlib import Path
d = Path(sys.argv[1]); P = json.load(open(d / "die_plan.json")); n = 0
NOTE = (" | DIE-HBM-10 10-28: stale 10-17 view (369.36x369.36, clocks USE SIGNAL) no longer cited for this 362.88x276.48 "
        "TRIAL outline -> PENDING-VIEW until its own view is signed off")
for tn in ("q_hub_nw", "q_hub_ne"):
    for h in P["partition_types"][tn]["hard_cores"]:
        if h["inst"] in ("u_xq_Q_p0_eg", "u_xq_Q_p1_eg"):
            assert h.get("lef") and h.get("lib"), (tn, h["inst"])
            h.pop("lef"); h.pop("lib"); h["note"] = h.get("note", "") + NOTE; n += 1
assert n == 4, n
txt = json.dumps(P, indent=1) + "\n"; (d / "die_plan.json").write_text(txt)
(d / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
print("view drop", n)
