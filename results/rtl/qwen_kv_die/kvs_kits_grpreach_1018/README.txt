KV-GRPREACH 10-18: lockstep witnesses of the KV group kits qkd_kvs_grp / qkd_kvs_grp_h (OT_KV_TILE_KITS=1 with the in-tile
through-word relays OT_KV_GRP_FT_RELAY=4 and the u_cf1 leg registers OT_KV_GRP_CF1_LEG=2) against the die-bound tile of the
same design point, with the kit-added edges taken from kv_static_die.kit_delays (o_dn[270:0] +4, o_ctl up field +4,
o_ctl cf1 bit +2 in phase A, u_cf1.fault_in +2).
Run: KVS_SIM=verilator bash tools/qwen_kv_die/kvs_tile_bench.sh OUT <grp|grp_h> M  on the fleet (ot-epyc5 via ot-run),
SIM Verilator 5.050 2026-07-01 rev v5.050 (the closure daemon's pin), source = this commit's parent tree + this commit.
m0 PASS errors=0; m1 dropped child wire, m2 swapped child inputs, m3 missing child, m4 o_dn relay chain one stage short,
m5 u_cf1 leg registers bypassed: all FAIL (both tiles).
