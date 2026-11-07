#!/usr/bin/env python3
"""DIE-KV-84 11-06: kv3_sys_SD + kv3_sys_SD_v1, sd_vA2 GRT gate (pin-keyed edge split, hold gate PASS -162.56) failed
G2 setup_tt -67.51: fstart cland_fstart_in_i_host_fdi -> ring write enable broadcast to the 524-bit WFALL ring
(u_cland_i_host_fdi u_ring.s_d[*]), half-cycle budget, place7059/7058 fanout 33/44.  Same class as kv3_io_ft (ftwreg_1104,
signed LOCAL_PASS_NEEDS_PARENT on that form): writer form WREG-1 on both SD rings (clock.landing_ring_wreg, strap K + 1 by
bind, 0 data cycles) + private status bank (landing_control_status_copy).  No outline or pin change.
Idempotent.  usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, sys
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
BUSES = ["i_host_fdi", "i_host_link_rst_n"]
a, b = sys.argv[1:3]
p = json.load(open(a))
for tn in TYPES:
    t = p["partition_types"][tn]
    t["clock"]["landing_ring_wreg"] = {"buses": BUSES, "dsrep": 1}
    t["landing_control_status_copy"] = True
json.dump(p, open(b, "w"), indent=1); open(b, "a").write("\n")
