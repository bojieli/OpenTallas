# HBM next-event plan d48a_postcut2_1111 (DIE-HBM-100, 2026-11-11) DO_NOT_COUNT

Plan die_plan.json.gz sha256 6391dea6a0b38710... (full sha in the queue READY): t11 (d47a, 584df6bfcfc2) + deltas/ in apply order:
1. DIE-LAYOUT-HBM 2x4 bank ladder c18 (ladder_delta format; apply with scripts/ladder_delta.py from claude/die-layout-hbm-1111@13839b31095b; on t11 gives 3a8a16e45bf2)
2. d10 xtap form D (HBM-VSN-XTAP-2, 8 types, 110 ops)  3. d11 nwio-ep-w52 (HBM-GEOM-2, 59 ops)
4. d13 revert CPL-HBM-2 q_su21 + pv1 (79 ops)  5. d14 revert CPL-HBM-2 lift q_spt0 + pv1 (746 ops)  6. d15 ptw-westwin-a form A (pt_w pin table, 64 ops + cores/...ptwW1111a.json)
Not included: neio-ep-e52r (conditional on ne_a30 DRC), B1 (needs the hub RTL part), q_su20pv1 M5, hub split.
Gates: strict bind on pure main (src_hbm_main_fe0002fac6, includes lat-derived, xtap support, PDN fix): pass 1 = 30 R8_STALE only, pass 2 with hbm_lat_pads.py table (hbm_arch_B2o_r8_landing_t19.json.gz, asbuilt_t19.json) BIND_OK n_errors 0 stale 0 uncovered 0 pad_flops 945867; loops SFU_VM NW 119 / NE 131 (ladder L5056 +8), HC_Q NW 137 / NE 150. Script results/hbm_cut_1111/bin/bind_t19.sh. G0 (main check.py) 642 (t11) -> 554: 37 new rows vs t11 = 21 known exceptions (6 b000 seam faces 6.6/um, 15 horizontal cuts <= 0.81) + 16 re-keyed, 0 new vs c16; route_supply q_sm0-3 unchanged 1.282/1.218.
