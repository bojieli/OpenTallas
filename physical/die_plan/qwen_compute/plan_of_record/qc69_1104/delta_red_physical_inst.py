#!/usr/bin/env python3
"""DIE-QC-69 11-04: QC RED hard core u_red_u_core sits inside the bound leaf u_u_red (qfd_dv_s5_red2p1_leaf.u_core), so
kit-rtl cannot find it by flat name.  Declare the kit-only physical identity on the 3 su_c types.  Idempotent; no bind,
pin, placement or schedule field changes.  usage: delta_red_physical_inst.py PLAN"""
import json
import sys

TYPES = ("sle_su_c", "slw_su_c__cl92142dac", "slw_su_c__cl19bb38ef")
path = sys.argv[1]
text = open(path).read()
plan = json.loads(text)
seps = next(sp for sp in ((", ", ": "), (",", ":")) if json.dumps(plan, separators=sp) + "\n" == text)
done = 0
for name in TYPES:
    t = plan["partition_types"][name]
    for c in t["hard_cores"] + t["contents"]:
        if c["inst"] == "u_red_u_core":
            c["physical_inst"], c["physical_master"] = "u_bound.u_u_red.u_core", "qfd_dv_s5_red2_leaf"
            done += 1
assert done == 6, done
open(path, "w").write(json.dumps(plan, separators=seps) + "\n")
print("entries", done)
