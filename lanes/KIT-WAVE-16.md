# KIT-WAVE-16 (kit-wave operator, succeeds KIT-WAVE-15)

Start 2026-11-01 19:10 PST. Scripts: hub intel2 /srv/opentallas-scratch2/claude/kit-wave-16/ (planfull.py = plan --probe with full lists, age.py = FAIL rows + age, inretry.py, lecsum.py, supersede16.py).

## 19:2x queue
- S81 sat at die cap 60/60 RUNNING with 77 eligible items (incl. slice_station__t41/t51 on the stnbank blocks, main 6defc3c2306); the other dies had 0 eligible; wave total 154/300 -> s81 die_max_inflight 60 -> 140 (coord 05d3d5802). 19:30 tick launched 40 (+2 QC); the rest follow on the next tick.
- ot-run 19:12: epyc2 9 waiters (load 85/128), intel1 138, intel2 98: every host has waiters.

## 19:5x COORD stale-FAIL triage (every FAIL row older than 6 h)
Before (19:2x, plan_current=yes): 93 FAIL rows, 75 of them older than 6 h. Each class gets one action:

| class (rows >6 h) | action | owner / ETA |
|---|---|---|
| HBM AUTO-GEOM vms_bank pin_density x6 + pgslice canon x3 + host_program + keybuf_slice | SUPERSEDED: newer lane kits in hbm-cores-kits-40/nk (8 of 11 logs written 19:2x) | HBM-CORES-KITS-40 lane builds |
| HBM opstore_a, programme_store_r10 (geom / GPL) | SUPERSEDED: live lane kits kits-38 opstore _k3, kits-37 pstore _k37g | HBM-CORES-KITS-37/38 |
| routed hold: hnx_fused_tnode | SUPERSEDED: OWNERS SIGNED | - |
| KV NO_RECIPE x4 (core_rx, phy_pad SIGNED; core_prompt, core_peer live lane jobs) | SUPERSEDED | KV-CORES / DIE-KV-60 |
| HEAD hd_st_m, hd_st_n4, hd_mesh_e, hd_st_k5 | SUPERSEDED: DIE-HEAD-53 lane builds (STm D LOCAL_PASS + LEC EQ; n4 PRD DRT; mesh_e S3 LOCAL_PASS; k5 prd53 B_p2) | DIE-HEAD-53 |
| QC place GPL-0305 x5 | BATCH RELAUNCH: retry @1 on all 5 (the 15:5x --gpl-plain type_args never relaunched because the records are block-keyed and had no retry entry) + --gpl-plain on sle_fw_v2__cl6740750e. 19:30 launched sle_fw_v2 x2; slw_fe_v2/slw_fw_v1 x2 launch when the sibling wave unit ends | KIT-WAVE-16 |
| S81 post-CTS FF structural hold x7 (10-31, real -137 ps / 5012 EP on t20, sources older than FLOW-19 hold_gate + ccband) + t12 sign-off NOT RUN | PILOT: slice_station__t20@3 + t12@5 relaunch on main 6defc3c2306; when the pilot reaches post-CTS, the other 5 go as one batch (t23 = live S81-PLAN canary; t24 x2 / t30 x2 / t40 have sibling classes ROUTING) | KIT-WAVE-16 pilot result ~23:xx; on FAIL -> DIE-S81-47 structural |
| S81 LP WAIT-DEP x3 (10-30, child lef without lib) | held by the wave dependency gate | S81-LP: ETA asked |
| HEAD geom aspect/fill/pin_reg x7 (hd_host_n, hd_spn, hd_spn_end, hd_spn_eshim_rx, hd_st_n3_transit/turn, hd_tile) + hd_turn_a cohort stale + hd_st_str post-CTS hold | wait for the HEAD l48y source event | DIE-HEAD-53: ETA asked |
| HBM geom/route/signoff singles (subtree32 pin_unreg, xload bfqg fill, svc_vmdel_lane_n GRT hold, idx_query_static setup+hold) | c11g plan event (DIE-HBM-57 c3bb4ef0c, READY) -> relaunch on it | DIE-HBM-57 / HBM-CORES-KITS-41: ETA asked |
| HBM no-flow-tag x2 (idx_tail_native, signed 10-31) | re-sign the same routed DB on a tagged flow (resign.py kind:resign) | HBM-CORES-KITS-41 |
| KV kv3_hub_Eo/Wo port_bind, qkd_hr_core_order NO_RECIPE, pv_join hold+drv | die plan/recipe fixes | DIE-KV-60: ETA asked |
| QC CB sdc_lint/strap x5 (held) | relaunch when DIE-QC-61 tools a945684312d merges | ROOT-MERGE-AL -> KIT-WAVE-16 |
| QC coll_ucie preflight, sle_sc_v1 DPL x2, tt_ctlm (held, class c897f9b902c) | die fixes | DIE-QC-62: ETA asked |
| S81 seqhost__t1 face_guard, kv_leaf__t2 memory bits, slice_station__t31 geom | die plan fixes | DIE-S81-47: ETA asked |
| LEC NOT EQUIVALENT x10 (HBM 7, QC 2, HEAD 1) | KIT-WAVE-16 takes it: every failing point has a gold-only register in its cone (no name-matched gate flop, e.g. split3 g_ld3k p1/p2/q2 missing from 1_2_yosys.v while p0/q01 are kept). Root cause and class fix in progress (helper) | KIT-WAVE-16 |

SUPERSEDED rows were written under kit_wave.lock (22 records, status CANCELLED class SUPERSEDED, reason names the newer kit).
