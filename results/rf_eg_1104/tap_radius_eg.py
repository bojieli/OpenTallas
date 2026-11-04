#!/usr/bin/env python3
"""S81 RF-EG (DIE-S81-54/EG 11-04): no single-tap move closes these two added taps after the reset trees were re-solved
(added_tap_recentre: iq_C__t1 clk_t30 216.16 um, c3x_C__t1 clk_t37 229.04 um, limit 200).  The far sink is a reset relay;
the radius is a target, so these two types declare clock.tap_radius_um.  Text edit, JSON equality asserted.
    python3 tap_radius_eg.py PLAN"""
import json, sys
f = sys.argv[1]; s = open(f).read(); p = json.loads(s)
for tn, r in (("dsdv_slice_iq_C__t1", 220), ("dsdv_slice_c3x_C__t1", 235)):
    assert "tap_radius_um" not in p["partition_types"][tn]["clock"], tn
    p["partition_types"][tn]["clock"]["tap_radius_um"] = r
    i = s.index(json.dumps(tn) + ":", s.index("\"partition_types\"")); j = s.index("\"tap_mode\"", i)
    s = s[:j] + "\"tap_radius_um\": %d, " % r + s[j:]
assert json.loads(s) == p, "text edit differs from dict delta"
open(f, "w").write(s); print("tap_radius_eg OK")
