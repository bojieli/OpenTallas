#!/usr/bin/env python3
"""DIE-KV-70 11-04: kv3_io_ft + kv3_io_ft_v1, ioftr routed read TT -211 on 2904 endpoints, all in the landing rings:
2880 on fstart -> ring write enable broadcast, 4 on ctl_w -> rv/lap_ok.  Writer form WREG-1 on all four ft rings
(clock.landing_ring_wreg, strap K + 1 by bind, 0 data cycles) + private status bank (landing_control_status_copy).
Idempotent.  usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, sys
TYPES = ("kv3_io_ft", "kv3_io_ft_v1")
BUSES = ["ft0_i", "ft1_i", "ft2_i", "ft3_i"]
a, b = sys.argv[1:3]
p = json.load(open(a))
for tn in TYPES:
    t = p["partition_types"][tn]
    t["clock"]["landing_ring_wreg"] = {"buses": BUSES, "dsrep": 1}
    t["landing_control_status_copy"] = True
json.dump(p, open(b, "w"), indent=1); open(b, "a").write("\n")
