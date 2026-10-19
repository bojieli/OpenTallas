TW2-KVGRP 10-19: lockstep witnesses of the KV group kits qkd_kvs_grp / qkd_kvs_grp_h (OT_KV_TILE_KITS=1: KV-GRPREACH in-tile
relays + the in-tile reset landing qkd_kv_rst_land, OT_KV_GRP_RST_RELAY=1) against the die-bound tile of the same design
point, + the leg registers (OT_KV_GRP_LEG=2 on every data input of u_bcdc0..3 / u_drain) and the landing-calendar
port relays (OT_KV_GRP_LCAL_RLY=1).  Kit-added edges from kv_static_die.kit_delays: o_dn +4, o_ctl up field +4, cf1 +2, bcdc0..3 / drain outputs +2 (child inputs +2), o_pc lcal r_* bits +1, and rst {rst_n: 3, hrst_n: 3}
(the bench releases the die-bound tile's reset ports 3 edges later, so both tiles' children leave reset on the same edge).
Run: KVS_SIM=verilator bash tools/qwen_kv_die/kvs_tile_bench.sh OUT <grp|grp_h> M on the fleet (ot-epyc6 via ot-run),
SIM Verilator 5.050 2026-07-01 rev v5.050 (the closure daemon's pin), source = the commit that adds this directory.
m0 PASS errors=0; m1 dropped child wire, m2 swapped child inputs, m3 missing child, m4 o_dn relay chain one stage short,
m5 u_cf1 leg registers bypassed, m6 core reset relay bypassed (children leave reset 3 edges early), m7 u_bcdc0 legs one stage short, m8 o_pc0 lcal
relay bypassed: all FAIL (both tiles).
