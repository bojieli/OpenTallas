# TYPES-S81-FAIL-1115 handoff (2026-11-15 07:1x PST)
Scope: S81 + HEAD failed / retry-infra / route-held types (STALE-TYPES-OPEN-1115.tsv: 24 s81, 2 s81_head) plus adopted dead lanes TYPE-S81-PHYROOM, S81-TAPSKEW, TL-HDHOSTW, TYPE-HDHOSTW-LEC, TL-LEAF42SETUP, TYPE-SLICET30, TYPE-S81LEAF29, TYPE-S81-GRTCAP, TYPE-SVCMEM, TYPE-COLH10R1, COL-SNAP-BUILD.
Method: last current-plan row of autopilot/kit_wave_stages.tsv + autopilot/OWNERS.tsv (live job) + kit_wave.json dies.s81.hold_items + DIE-S81-92-delta.tsv + S81-release-60.tsv.

## Findings
- The STALE list was stale: 12 of the 26 rows already have a live autopilot job (OWNERS 06:36). Every row without a live job is either (a) under a KIT-OPS-5 PENDING-PLAN hold (350 delta types, all covered, 0 uncovered), (b) a FABLE stop-list hold (leaf, serdes t15 clone, hd_host_e), (c) S81-COL-INHERIT held, or (d) an unchanged parent row the wave retries by itself (RETRY-INFRA).
- The only 3 S81-release-60 types with no live job (ot_s81sl_leaf__t27, ot_s81sl_leaf__t42, phy__t1) carry PENDING-PLAN keys set 11-15 by OWNER via COORD r50 ("no new launch or retry until adoption, then regenerated fresh"). I did not lift them: lifting contradicts that ruling and the kit inputs change under B6gsl. They relaunch at adoption. serdes__t12 (release-60 and delta) is the same, it has a live attempt.
- Class ot_store (7 leaf types, 11-14 23:05-23:55): fixed by KIT-OPS-5 branch claude/kit-ops-5-otstore-1114 @74171a9e5919 (COORD APPROVED), nothing to do but relaunch after adoption.
- Adopted lane results found on disk (no reader since the 11-14 19:43/22:45 crashes):
  * slice_station__t37 form c (epyc8 /srv/opentallas-scratch2/claude/typeslicet37/c, density 0.35, M9, -allow_congestion): SIGNED (minimal profile, TT +5.81, FF hold -7.99 sdc -47.76, DRC 0), signed 11-15 ~04:13. Archived to rtx-pro + AGIdock, sha256 equal (INDEX row ARCHIVED-BOTH-NO-VIEWPACK) (status ARCHIVED-BOTH-NO-VIEWPACK). AUTO-RESIGN row added.
  * slice_station__t8 c / t24 c / t28 c: NOT SIGNED (FF hold -77 / -66 / -84). Those types already have archived signed records (t8, t28, t24 cl66b71008/cleece78ec); FABLE-HARD-S81 19:05 said rebuild t28/t36/t27 on B4L4 at adoption. No action.
  * slice_station__t30 c SIGNED 11-14 15:42, archived (INDEX rows TYPE-SLICET30). t52 c died exit 2 in GRT, peak 31.75 GB at the 32 GB kit cap (memory, not design); t52 is held PENDING-PLAN.
  * ot_s81sl_leaf__t29 formB10 (epyc10 type-s81leaf29/formB10): LIVE, GRT extra iteration 18/30, 20 h old. Left running (exact container oth-ubuntu-3572362-1794682948, pid 3572509). t40f/t21f/t25af10/t25bf/t44f10 forms are dead (DRT-0255 pin access, t44f10 GRT fail); DBs kept at epyc10 type-s81leaf29/{t40f,t21f} for GRT-resume with OT_PG_DIE_PHASE=1 OT_PG_CELL_KEEPOUT=1 (PG-AWARE-1 @8e7457814f).
  * type-colh10r1 forms fa/fb/fc/fd: all dead (no process). fa/fc/fd logs show repair at setup WNS -328..-346 ps TNS -1.3M on u_bound.u_lpad_frame_int_i1 (design, hot strip). Siblings held by COL-INHERIT + delta.
  * TL-LEAF42SETUP: t42/t6 overlay kits ran; t42 route FAIL FLOW EST-0005 after 5:03 h GRT (run/logs .../5_1_grt.log line 849, "Run global_route before estimating parasitics", exit after Repair antennas). sim run_sim.sh on intel1 (pid 3466905, 24 h) is still running with no reader; left alone.
  * TYPE-S81-GRTCAP: private form A not on disk (kit dir missing on epyc2/intel1); kv_leaf__t4 held PENDING-PLAN, last row INFRA gen STALE-CORE-VIEW. Plan stays: OT_GRT_POST_MAX_S=0 at relaunch.
  * TYPE-SVCMEM: svc_hi/lo rs t1-t7 + pvso t1/t2 all PENDING-PLAN held; 15 have live attempts; private m2r/noshare builds on epyc8/epyc9 are gen-only dirs, no process.
  * TYPE-S81-PHYROOM: no builds. Finding: option (b) infeasible, phy room must come from (c) bus-window alignment; die channels stale at the old outline. DIE-S81-92 owns.
  * S81-TAPSKEW: no handoff file; result lanes/S81-TAPSKEW.tsv (RESULT 11-14 06:24), superseded by FABLE-REVIEW-CLK R-CLOCK-7. Nothing live.
  * TYPE-HDHOSTW-LEC: branch claude/type-hdhostw-lec-1114 @c327d8dfb2cb is already in the HEAD src (src_head_rp21z_pgcaplec_c327). TL-HDHOSTW form B (outline +30% north, 648x740.88) never ran (needs a plan event); HEAD-99 owns hd_host_w/e (HEAD die-wide hold until HEAD-99 posts).
  * COL-SNAP-BUILD: cancelled 11-14 08:35, nothing live.
- phy__t1: route FAIL FLOW exit 1 straight after 4_1_cts (16 min CTS, 38 GB), cell census 1.2M projected non-tap cells = 301.8% of the 400k cap (advisory). Size class, held PENDING-PLAN.

## Table (type | last real failure class | action)
| type | class | action |
| col_h9_r0_p6__t1 | procedural (bind no partition type on old plan, superseded) | live job ap-fb19f36c89d1 (12 pv in release-60, live) |
| col_h9_r0_p1__t1 | held | S81-COL-INHERIT HELD-STOP + delta CHANGED; wait adoption |
| col_h9_r0_p2__t1 (+cl0045af7b, cl9f71e63d) | procedural (exit 143 kit_rtl, plan superseded) | clones held PENDING-PLAN; parent RETRY-INFRA wave retry |
| col_h9_r0_p3__t1 (cl8ce97bcb) | procedural | live job ap-780b734f6f8a |
| col_h10_r2__t1 (cl8b686b3e) | superseded | held S81-COL-INHERIT; rep pv9ae398c2 live |
| serdes__t3 / t12 / iqf__t1 / dsdv_slice_lepw_mus_LP__t2 / leaf t4 / leaf t59 | live | routing jobs, nothing to do (serdes t3/t12/iqf/leaf t4/t59 carry PENDING-PLAN; running attempts finish) |
| serdes__t2 | design (a27 geometry, KP4 island, HARD-S81-SERDES-1) | PENDING-PLAN held; fix is the B6gsl serdes plan |
| serdes__t1 (clfe1f0815), serdes__t15 (cla2127225, cla3d02796), t13, t16 | procedural orphan (t1) / plan design (PG domain phy_lk_EN holds no macro) | held PENDING-PLAN / FABLE stoplist; delta has other:phy_pg_macros; owner DIE-S81-92 |
| slice_station__t49 | live (TYPE-SLICE-HOLD job 842d85fc46f0) | none |
| slice_station__t36 / t43 / t52 | procedural (exit 143, orphan, t52 32 GB OOM in GRT) | PENDING-PLAN held; relaunch at adoption with mem 56 |
| slice_station__t37 | design (GRT congestion) -> SOLVED | private form c SIGNED TT +5.81 FF -7.99; archive in progress; AUTO-RESIGN row; tell FABLE-PD-S81T |
| ot_s81sl_leaf__t3 / t23 / t27 / t38 | procedural (STALE-CORE-VIEW, ot_store x2, orphan) | class ot_store fixed (kit-ops-5-otstore); held stoplist + PENDING-PLAN |
| ot_s81sl_leaf__t42 | procedural/flow (EST-0005 after 5 h GRT) | held; NEEDS-LANE posted |
| ot_s81sl_leaf__t21 / t25 / t40 / t29 / t44 | design (DRT-0255 pin access, PG under M5xM6) | held PENDING-PLAN; fix known PG-AWARE-1, NEEDS-LANE posted; t29 formB10 live |
| ot_s81sl_kv_leaf__t2 | live | placing, held for retries |
| phy__t1 | flow exit 1 after CTS, 301.8% cell cap | held PENDING-PLAN; NEEDS-FABLE posted (size) |
| hd_host_e | procedural exit 143 (stop from outside); stoplist a13 u_epc tap 42 vs 442 | held (Fable stoplist, HEAD-99 owns); release with PG-rule-merged rebuild |
| hd_host_w | design (GRT-0116 overflow, route attempt_9, rp21z4) | HEAD-99 owns (plan rp21z19/z20); NEEDS-LANE: adopt TL-HDHOSTW form B growth |
