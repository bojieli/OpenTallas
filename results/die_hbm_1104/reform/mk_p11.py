#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 11: split3 fr table without sfu_vi_q[31:24]. mk_p11.py PLAN_DIR
Same class as q2r in part 9. The 8 bits are unread by the fr core and dropped by the face shell (face_shell.json dropped 8,
fshell ties them {8'd0, ...}), so the signed-off record has no such pins and counts as core, not design. The other 1549
pins are unmoved. 32 rows take the new table; no outline, macro or other row changes."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1])
Q = "cores/ot_hgi_sfu_split3_lane_core_fr__120.96x345.6__d44v_split"
DROP = {f"sfu_vi_q[{i}]" for i in range(24, 32)}
T = json.loads((pd / (Q + ".json")).read_text())
keep = [p for p in T if p["name"] not in DROP]
if len(T) - len(keep) != 8: raise SystemExit(f"fr drop {len(T) - len(keep)} != 8")
(pd / (Q + "__vi24.json")).write_text(json.dumps(keep))
D = json.loads((pd / "die_plan.json").read_text()); k = 0
for ty in D["partition_types"].values():
    for c in ty.get("hard_cores") or []:
        if c.get("pins_file") == Q + ".json": c["pins_file"] = Q + "__vi24.json"; k += 1
if k != 32: raise SystemExit(f"fr rows {k} != 32")
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
(pd / "part11_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part11",
    "core": "ot_hgi_sfu_split3_lane_core_fr", "moved": {Q + "__vi24.json": k}, "dropped": sorted(DROP)}, indent=1) + "\n")
print("part 11", k, "rows", len(keep), "pins")
