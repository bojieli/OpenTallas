#!/usr/bin/env python3
"""S81 RF-EG (DIE-S81-56/PLAN 11-04): same class as xf_lib.py: u_c.u_xr (ot_s81sl_xrt3) in the two C types that use it has a LEF
and no lib, so gen refuses the kit.  Adds the TT lib of the view the LEF comes from.  Text edit, nothing else moves."""
import json, sys
p = sys.argv[1]; s = open(p).read()
a = '{"inst":"u_c.u_xr","module":"ot_s81sl_xrt3",'
b = a + '"lib":"physical/ref_tile/s81sl_xrt3_b/views/ot_s81sl_xrt3/ot_s81sl_xrt3_tt.lib",'
assert s.count(a) == 2, s.count(a)
s = s.replace(a, b)
json.loads(s); open(p, "w").write(s); print("xr_lib", 2)
