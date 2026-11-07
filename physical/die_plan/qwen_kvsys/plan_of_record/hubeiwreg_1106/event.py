#!/usr/bin/env python3
"""KV-IOCOR-2 11-06: kv3_hub_Ei, version A after 2 failed route attempts (attempt_3 FF hold -458.64 / 30,550 endpoints,
attempt_5 G2 setup_tt -164.85 with the GRT hold guard on 34,527 endpoints).  All 81 rings already carry ring_place ff
(no plain wide ring left).  attempt_5 G2 TT violators 2-4 are the kv3_io_ft / sys_SD / io_cor class:
cland_fstart_in_ft{36,63,64}_i -> ring s_d write enable (-14.12 / -21.36 / -101.62).  Writer form WREG-1 on all rings
(clock.landing_ring_wreg, strap K + 1 by bind, 0 data cycles) + private status bank (landing_control_status_copy).
The worst violator (-164.85, ring u_cland_i_hp_fault_N_q read -> u_bin_i_hp_fault_N_q, ~780 ps of repeated wire) is a
placement-locality item, not this class.  The safe form (version B) is a split (est 289,525 cells > 150k cap), proposed
as its own plan event.  No outline, pin or rect change.  Idempotent.  usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, sys
a, b = sys.argv[1:3]
p = json.load(open(a))
t = p["partition_types"]["kv3_hub_Ei"]
bands = t["clock"]["landing_contract"]["bands"]
rings = sorted(k for k, v in bands.items() if not k.startswith("monitor_") and v.get("rect_um"))
t["clock"]["landing_ring_wreg"] = {"buses": rings, "dsrep": 1}
t["landing_control_status_copy"] = True
json.dump(p, open(b, "w"), indent=1); open(b, "a").write("\n")
