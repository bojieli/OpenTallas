#!/usr/bin/env python3
"""CPL-S81-SLICE-3 stage c_bands: set clock.landing_contract.bands[name].rect_um (same face edge, same window;
only the inward extent changes).  usage: apply_bands.py IN_PLAN BANDS.json OUT_PLAN"""
import json, sys
P = json.load(open(sys.argv[1])); B = json.load(open(sys.argv[2]))
for tn, m in B.items():
    bd = P["partition_types"][tn]["clock"]["landing_contract"]["bands"]
    for k, r in m.items():
        old = bd[k]["rect_um"]
        assert any(abs(a - b) < 1e-6 for a, b in zip(old, r)), (tn, k, "band must keep its face edge")
        print(tn, k, old, "->", r); bd[k]["rect_um"] = r
json.dump(P, open(sys.argv[3], "w"), separators=(",", ":"))
