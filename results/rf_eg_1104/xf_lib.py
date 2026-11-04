#!/usr/bin/env python3
"""S81 (DIE-S81-54/EG 11-04): u_c.u_xf has a lef but no lib in the 16 C types (also on main), so gen stops with
"macros have LEF but no timing liberty".  Add the signed view TT lib path, same form as the other cores.
Text edit, JSON equality asserted.    python3 xf_lib.py PLAN"""
import json, re, sys
f = sys.argv[1]; s = open(f).read(); p = json.loads(s); n = 0
L = "physical/ref_tile/s81dv_xfin/views/ot_s81dv_xfin/ot_s81dv_xfin_tt.lib"
for t in p["partition_types"].values():
    for c in t.get("hard_cores") or []:
        if c.get("module") == "ot_s81dv_xfin":
            assert "lib" not in c; c["lib"] = L; n += 1
assert n == 16, n
s, a = re.subn(r"(\"lef\":\s*\"physical/ref_tile/s81dv_xfin/views/ot_s81dv_xfin/ot_s81dv_xfin\.lef\",?)", lambda m: "\"lib\": \"%s\", %s" % (L, m.group(1)), s)
print("rows", n, "text", a)
assert json.loads(s) == p, "text edit differs from dict delta"
open(f, "w").write(s); print("xf_lib OK")
