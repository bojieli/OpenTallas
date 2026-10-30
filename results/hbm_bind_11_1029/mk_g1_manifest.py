#!/usr/bin/env python3
"""HBM-BIND-11 g1 manifest = DIE-HBM-23 b2 manifest (HBM-BIND-7 c1) + native_glue_types += $div. Nothing else changes."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]   # .../die-hbm-23/b2/asbuilt.json  .../hbm-bind-11-1029/g1/asbuilt.json
m = json.load(open(src))
assert m["native_glue_types"] == ["$shift", "$shiftx"], m["native_glue_types"]
m["native_glue_types"] = ["$shift", "$shiftx", "$div"]
m["note"] = ("HBM-BIND-11 g1: c1 + native_glue_types += $div (hub HC dissolved qcen in_w / NJ, NJ = W/32 constant; "
             "bind_native_glue SUPPORTED, emitted as Yosys write_verilog of the cell, no mapping) | " + m["note"])
json.dump(m, open(dst, "w"), indent=1)
