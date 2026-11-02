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
| LEC NOT EQUIVALENT x10 (HBM 7, QC 2, HEAD 1) | ROOT CAUSE (6 of 10): no-reset register loaded only with a constant is folded by yosys, LEC drops the constant hypothesis (10-27 power-up X), its readers differ. FIX claude/kit-wave-16-lec-1101@801a1c2a09f (auto 'loaded' valid-flag hypothesis, induction-proved) READY 19:4x. After merge + deploy: batch relaunch all 10 (all ran an old lec.py). Residual classes: kshare x2 gray-FIFO/CDC, q2n2 reference netlist, slw_st_b SRAM write-data | KIT-WAVE-16; merge ETA = next ROOT-MERGE-AL train |

SUPERSEDED rows were written under kit_wave.lock (22 records, status CANCELLED class SUPERSEDED, reason names the newer kit).

## 20:08 hourly class table (plan_current=yes)
FAIL 64 (19:2x: 93), older than 6 h 53 (75). RUNNING: s81 147, qc 46, kv 29, hbm 19, head 7. Classes of 3 or more:

| class | n | owner / fix | ETA |
|---|---|---|---|
| HBM LEC NOT EQUIVALENT (+QC 2, HEAD 1) | 6+1+2+1 | KIT-WAVE-16: claude/kit-wave-16-lec-1101@801a1c2a09f READY, not merged by 20:04 (main 1923c5d) | batch relaunch of all 10 on the next ROOT-MERGE-AL train |
| S81 slice_station post-CTS hold | 6 | pilot t20@3 + t12@5 RUNNING on 6defc3c | batch after pilot post-CTS (~23:xx); on FAIL -> DIE-S81-47 |
| HEAD geom aspect/fill x6 + hd_tile | 7 | DIE-HEAD-53 l48y source event | asked |
| KV kv3_pv_v1..v4 ORD-2013 (NEW) | 4 | DIE-KV-60: LEF master ot_sram_1r1w_32x128_m1 missing from the pv kit LEF list (u_pv_u_g0_b0.u_slice.g_mem[0].u_mem); src efa6a9b already has the kv-macro fix 1adcd26, so this is a separate class -> one recipe/LEF fix + batch relaunch of 4 | asked |
| QC CB sdc_lint x3 + strap + cbf_q11 | 5 | DIE-QC-62 class c897f9b902c (unmerged) | next train |
| QC place GPL-0305 slw_fe/fw x3 | 3 | retry @1 queued; blocked by sibling units (slw_fe_v2__clf110fab2, slw_fw_v1__clf51c11d8__clc7ddab13) that have WAITED 8 h at gen_lint behind the intel2 load cap | after the siblings run |
| S81 LP WAIT-DEP x3 | 3 | S81-LP | asked |
| HEAD post-CTS hold x3 | 3 | DIE-HEAD-53 | asked |
| S81 col_h9 kit_rtl x2 (NEW, singles >6 h) | 2 | DIE-S81-47: kit-RTL bind of record still names /srv/.../codex-s81-wave-1131/src/physical/rom* (pruned); retries @3/@2 repeat it -> repoint kit_rtl at the current strict bind | asked |

Infra (FLOW-21): intel2 load1 ~300 vs cap 168 (1.5 x 112, mostly DRT) -> admissions fell 104/h (13:xx) -> 19/h (19:xx); 100 waiters; 2-thread gen_lint jobs have waited 8 h; review renders NOT RUN (load cap 120 s). Ask: let short low-thread kit stages (<= 2 threads) skip the cap, or route hub stages to epyc2/intel1.
NEAR-COUNT duty (6): claude/kit-wave-16-nearcount-1101@bc6e04cda1c READY (inert until lanes/NEAR-COUNT.tsv exists).
