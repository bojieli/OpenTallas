# ELEM-S81 lane (claude/elem-s81-1024, worktree localhost:~/wt/elem-s81; run root /srv/opentallas-scratch/claude/elem-s81)
Scope (COORD owner correction 10-24): S81 v4.8 layer die + head die AS PLANNED: partition types / hard cores with no
signed closed view through the new kit gates (main 4b7b2b3e64+), excluding S81 (7 frame kits), S81-CORES (91 G0C hard
cores: 74 ot_s81sl_leaf types, 16 svc, eng), S81-HEAD (head tiles). Sign-off (OWNER 08:10): setup TT / hold FF (never SS), 833 ps, 60/25, spread <= 80.
The 10-21 element list is obsolete (no job was started from it).

## Inventory (main 4b7b2b3e64, check.py --completeness: G0C 83/174 types clean = G3-eligible)
Proposed ELEM-S81 list (76 G3-eligible types minus S81's 7 frames):
- frames x5: col_h9_r0_p2/p4/p5/p6__t1, col_h10_r0_p4__t1 (same contents as S81's p1/p3 kits; S81: confirm you do not run them)
- slice_station__t1..t34 (34 ft-only types)
- needs a v4.8 BIND first (gen.py phys refuses: buses not leaf-bound in the plan; BINDER4 bind is on v4.6 and its
  b3r8 outputs were lost with the old scratch): bk_col, bk_sel, gunit, iqf, seqhost, serdes__t1..t6, phy,
  ot_s81sl_kv_leaf__t1..t5, dsdv_slice_{c1x_C t1-9, c3x_C, iq_C, kv512_C, lepe_mu_C/LP, lepe_nh_mus_C/LP, lepw_mu_C/LP, lepw_mus_C/LP}
- head die (s81_head): non-tile types once S81-HEAD confirms (hd_turn_a/b, hd_st_*, hd_spn*, hd_serdes, hd_mesh/ctl/host/lep0N)
Not mine: S81 7 frames; S81-CORES 74 leaf + 16 svc + eng types (G0C fails) and their core kits; head hd_tile (S81-HEAD).

## Overlap check (08:20 PDT, COORD ask)
S81's 7 regenerated frame kits (docker dpkit-*, launched 07:38): col_h9_r0_p1, col_h9_r0_p3, col_h9_r1, col_h9_r2,
col_h10_r0_p1, col_h10_r1, col_h10_r2 (localhost/intel1/intel2/epyc3). Mine: col_h9_r0_p2, col_h9_r0_p4, col_h9_r0_p5,
col_h9_r0_p6, col_h10_r0_p4 = DIFFERENT plan types (own pin tables / ft slots; same r0 content module). No overlap -> kept.
Hosts: mine are ot-run admitted (memory), 16 thr per frame (intel1 x2, intel2 x2, localhost x1) + 4 thr per station.
## Current step
1. Proposal posted (S81-CORES/S81/S81-HEAD). Kits gen OK (39). face_guard false FAIL on 1-station ft slots fixed + merged main 6ba0c8b80c. 39 kits routing.
## Run dirs
- kits (gen.py phys @main 4b7b2b3e64 + face_guard fix): localhost:/srv/opentallas-scratch/claude/elem-s81/kits/<type>
  (same path on intel1/intel2, synced back at end). Launcher bin/launch.sh (ot-run --hosts H pinned), log kits/launch.log.
- retry watcher localhost pid 967712 (bin/retry_watch.sh): relaunches OOM'd routes at 2x mem (>=28 GB); kits/retry.log.
  slice_station at 12 GB OOMs in GRT/DRT init (peak 12.6 GB) -> retried at 28 GB.
- bind48 sub-agent: S81 v4.8 as-built bind + kit-rtl for the non-frame types (branch claude/elem-s81-bind48-1024).
## SIGNOFF NEEDS RE-RUN campaign (COORD 08:15): S81 hard cores with kits in repo -> 4 sub-agents (review -> route via job.json stages -> signoff.py --corners tt,ff)
- batch A gunit l0/l0r/l1/l1c/l2/l3/l4/l4r/l5(spread fix)/l5f; batch B bk_g, bksel_c, bksel_q, xfin, capc5r, eg, xrt1, xrt3;
  batch C cfifo_crs4, node LLd/LLfd/LLfu/NNfd/NNfu, rstg; batch D qbank_N/S, cfg7_seq/_bfp, sstn_base566/payload536, head spo/spr.
  Run dirs /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/ (localhost/epyc2/epyc3), reviews hc/reviews/<kit>.json.
- NO kit in repo (blocked, not run): dsdv_eng_tap, dsdv_eng_tap_w, dsdv_idx_tx_n32, dsfd_bf_front_roots, ot_v41_bf_col,
  ot_v41_rom_elem_q_qxpq_w10 (+ head ot_dsrom_head_elem). Need kit recovery from branches/specs.
## Station kit reviews (08:30, owner 08:05 order): 33 slice_station PASS-COND, t19 N/A (empty filler, no ports/logic) ->
  results/geom_review/s81_g3_slice_station__t*.json (branch). OOM'd routes relaunched at 28 GB (epyc3/localhost).
## Results
## OWNER?

## From S81 (2026-10-24 08:10 PDT)
Go ahead: I do NOT run col_h9_r0_p2/p4/p5/p6 or col_h10_r0_p4, and I have NO v4.8 bind -- take the BINDER4 bind.
My 7 frame kits (h9_r0_p1/p3/r1/r2, h10_r0_p1/r1/r2) are regenerated through CP1-R10 sdc_lint/face_guard (main 4b7b2b3e64)
and routing now. Heads-up: sub-lane S81-XDIE (claude/s81-xdie-1024) is adding the copy-A/B reserve SerDes pair
(lk_EN2/3, lk_WS2/3) to the layer-die plan for all dies, so serdes / lk_* / the LP slices that terminate copyb may change:
hold those types until it lands (S81.md "S81-XDIE" section).

## SIGNOFF re-signoff list (2026-10-24 08:04 PDT, main 4ab1ec1399, results/signoff_1024/) — SUPERSEDED by the SIGNOFF list below (rec SS there was the TT slack)
Recipe: tools/die_plan/signoff.py (TT setup / FF hold with std boundary-hold overlay / TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna). Routed DBs of every closed block were on the wiped old fleet -> NEEDS RE-RUN; re-close from the kit and run `signoff.py run --run-dir <run> --out <dir>` before calling it closed.

### s81: 37 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 37
- last record already FAILS the standard (re-close, not just re-STA): dsdv_gunit_l5 (recorded TT pin-flop spread 101.9 ps > 80, recorded FF pin-flop spread 95.3 ps > 80)
- NO kit in repo (6): dsdv_eng_tap, dsdv_eng_tap_w, dsdv_idx_tx_n32, dsfd_bf_front_roots, ot_v41_bf_col, ot_v41_rom_elem_q_qxpq_w10
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): dsdv_bk_g x1 (17.77/6.59, 67.5/59.6); dsdv_bksel_c x1 (54.58/8.99, 51.6/48.5); dsdv_bksel_q x4 (37.37/5.16, 65.9/61.2); dsdv_eng_tap x15 (38.55/22.75, 24.8/23.3); dsdv_eng_tap_w x1 (76.26/19.93, 21.9/21.0); dsdv_gunit_l0 x1 (198.78/5.63, 58.2/55.6); dsdv_gunit_l0r x1 (24.55/24.06, 12.5/12.6); dsdv_gunit_l1 x1 (59.31/2.71, 76.0/73.7); dsdv_gunit_l1c x1 (0.11/16.71, 36.2/36.3); dsdv_gunit_l2 x1 (74.7/4.99, 48.9/47.3); dsdv_gunit_l3 x1 (133.72/10.01, 61.0/58.5); dsdv_gunit_l4 x1 (71.87/5.94, 52.8/52.0); dsdv_gunit_l4r x1 (144.14/18.96, 10.6/10.1); dsdv_gunit_l5 x1 (20.6/20.07, 101.9/95.3); dsdv_gunit_l5f x1 (151.76/22.01, 11.4/11.0); dsdv_idx_tx_n32 x1 (None/None, None/None); dsfd_bf_front_roots x228 (0.0/18.2, 9.9/8.4); dsfd_cfifo_crs4 x72 (40.3/11.34, 61.3/60.6); dsfd_node_LLd x72 (95.22/23.29, 12.8/13.1); dsfd_node_LLfd x504 (89.29/18.49, 13.1/12.7); dsfd_node_LLfu x516 (84.29/22.89, 16.3/17.1); dsfd_node_NNfd x516 (100.18/16.83, 14.2/14.3); dsfd_node_NNfu x504 (90.08/12.49, 25.1/24.1); dsfd_qbank_N x864 (332.23/1.58, 2.8/3.1); dsfd_qbank_S x864 (214.61/21.41, 12.8/13.1); dsfd_rstg x216 (328.42/30.99, 1.2/1.4); ot_s81_cfg7_seq x864 (321.2/25.53, 12.0/11.3); ot_s81_cfg7_seq_bfp x228 (244.26/23.88, 14.4/13.5); ot_s81_sstn_base566 x660 (329.25/24.82, 14.5/14.5); ot_s81_sstn_payload536 x660 (344.2/26.61, 8.8/9.0); ot_s81dv_xfin x16 (4.78/11.46, 57.8/56.2); ot_s81sl_capc5r x16 (326.69/13.38, 0.0/0.0); ot_s81sl_eg x16 (71.85/16.24, 10.1/10.6); ot_s81sl_xrt1 x15 (40.44/9.45, 69.1/64.5); ot_s81sl_xrt3 x1 (9.5/10.86, 64.1/54.4); ot_v41_bf_col x456 (63.59/6.24, 44.4/32.6); ot_v41_rom_elem_q_qxpq_w10 x864 (116.28/12.25, 50.2/38.2)

### s81_head: 3 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 3
- NO kit in repo (1): ot_dsrom_head_elem
- NEEDS RE-RUN (module x instances, rec SS/FF ps, rec spread TT/FF): ot_dsrom_head_elem x1320 (133.67/10.81, None/None); ot_s81hd_spo x6 (19.69/40.87, 78.0/72.9); ot_s81hd_spr x6 (373.03/32.35, 48.3/44.9)
- surviving routed runs signed: dsdv_eng_rr_h0 NOT SIGNED (SS -396.55 ps/5108 ep, FF hold std -20.76, TT +8.05 = ORFS, face_guard shared 68, sdc_lint 2), dsdv_eng_rr_h1 NOT SIGNED (SS -377.41, FF -32.70, TT +13.90); CP1 r10a col_h10_r1__t1 NOT SIGNED (SS -462, FF -45.7, TT -212, face_guard dropped 120)

## bind48 (sub-agent)
- 08:15 setup: branch claude/elem-s81-bind48-1024 (localhost wt /srv/opentallas-scratch/claude/elem-s81/wt-bind48); run dir intel2:/srv/opentallas-scratch2/claude/elem-s81/bind48 (wt = detached main 2c4e32da32, plan v4.8 sha ea36999b). asb rebuilt from recovered cap30 die.v (sha 64d4be88): 72 frames, 482 clock ports; map 659 = identical to v4.6 asbuilt_map_s81.json. elab (yosys 0.68) launched via ot-run intel2 --mem 64.

## [SUPERSEDED: SS-based, owner 10-24 rule is TT setup / FF hold] SIGNOFF re-signoff list v2 (2026-10-24 08:06 PDT, main 0f5176689d, results/signoff_1024/README.md + per_die.md)
Recipe tools/die_plan/signoff.py: SS setup, FF hold (std overlay: out min 0 / in min -40), TT report, DRV, unconstrained, pin-flop spread <= 80 TT+FF, sdc_lint, face_guard, DRC/antenna. Every closed block's routed DB was on the wiped old fleet -> NEEDS RE-RUN. NOTE: closure_loop verdicts were accepted at TT setup; 'rec SS' below is the SS-library slack (metrics.ss_sensitivity_ps). Paper FAIL = re-close needed (not just re-STA). After re-close: `signoff.py run --run-dir <ORFS run> --out <dir>` must say SIGNED.

### s81: 37 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 37 (paper FAIL 29, paper PASS 7)
- dsdv_bk_g x1: NEEDS RE-RUN | rec SS -295.16 (TT 17.77) FF 6.59 spread TT/FF 67.5/59.6 | kit repo | paper FAIL
- dsdv_bksel_c x1: NEEDS RE-RUN | rec SS -302.7 (TT 54.58) FF 8.99 spread TT/FF 51.6/48.5 | kit repo | paper FAIL
- dsdv_bksel_q x4: NEEDS RE-RUN | rec SS -309.48 (TT 37.37) FF 5.16 spread TT/FF 65.9/61.2 | kit repo | paper FAIL
- dsdv_eng_tap x15: NEEDS RE-RUN | rec SS -187.47 (TT 38.55) FF 22.75 spread TT/FF 24.8/23.3 | kit NOT IN REPO | paper FAIL
- dsdv_eng_tap_w x1: NEEDS RE-RUN | rec SS -213.88 (TT 76.26) FF 19.93 spread TT/FF 21.9/21 | kit NOT IN REPO | paper FAIL
- dsdv_gunit_l0 x1: NEEDS RE-RUN | rec SS -52.16 (TT 198.78) FF 5.63 spread TT/FF 58.2/55.6 | kit repo | paper FAIL
- dsdv_gunit_l0r x1: NEEDS RE-RUN | rec SS -310.65 (TT 24.55) FF 24.06 spread TT/FF 12.5/12.6 | kit repo | paper FAIL
- dsdv_gunit_l1 x1: NEEDS RE-RUN | rec SS -263.71 (TT 59.31) FF 2.71 spread TT/FF 76/73.7 | kit repo | paper FAIL
- dsdv_gunit_l1c x1: NEEDS RE-RUN | rec SS -371.01 (TT 0.11) FF 16.71 spread TT/FF 36.2/36.3 | kit repo | paper FAIL
- dsdv_gunit_l2 x1: NEEDS RE-RUN | rec SS -197.32 (TT 74.7) FF 4.99 spread TT/FF 48.9/47.3 | kit repo | paper FAIL
- dsdv_gunit_l3 x1: NEEDS RE-RUN | rec SS -195.47 (TT 133.72) FF 10.01 spread TT/FF 61/58.5 | kit repo | paper FAIL
- dsdv_gunit_l4 x1: NEEDS RE-RUN | rec SS -281.11 (TT 71.87) FF 5.94 spread TT/FF 52.8/52 | kit repo | paper FAIL
- dsdv_gunit_l4r x1: NEEDS RE-RUN | rec SS -162.6 (TT 144.14) FF 18.96 spread TT/FF 10.6/10.1 | kit repo | paper FAIL
- dsdv_gunit_l5 x1: NEEDS RE-RUN | rec SS -2935.05 (TT 20.6) FF 20.07 spread TT/FF 101.9/95.3 | kit repo | paper FAIL
- dsdv_gunit_l5f x1: NEEDS RE-RUN | rec SS -162.9 (TT 151.76) FF 22.01 spread TT/FF 11.4/11 | kit repo | paper FAIL
- dsdv_idx_tx_n32 x1: NEEDS RE-RUN | rec SS - (TT -) FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD
- dsfd_bf_front_roots x228: NEEDS RE-RUN | rec SS -292.83 (TT 0) FF 18.2 spread TT/FF 9.9/8.4 | kit NOT IN REPO | paper FAIL
- dsfd_cfifo_crs4 x72: NEEDS RE-RUN | rec SS -150.37 (TT 40.3) FF 11.34 spread TT/FF 61.3/60.6 | kit repo | paper FAIL
- dsfd_node_LLd x72: NEEDS RE-RUN | rec SS -242.37 (TT 95.22) FF 23.29 spread TT/FF 12.8/13.1 | kit repo | paper FAIL
- dsfd_node_LLfd x504: NEEDS RE-RUN | rec SS -257.04 (TT 89.29) FF 18.49 spread TT/FF 13.1/12.7 | kit repo | paper FAIL
- dsfd_node_LLfu x516: NEEDS RE-RUN | rec SS -271.75 (TT 84.29) FF 22.89 spread TT/FF 16.3/17.1 | kit repo | paper FAIL
- dsfd_node_NNfd x516: NEEDS RE-RUN | rec SS -249 (TT 100.18) FF 16.83 spread TT/FF 14.2/14.3 | kit repo | paper FAIL
- dsfd_node_NNfu x504: NEEDS RE-RUN | rec SS -259.48 (TT 90.08) FF 12.49 spread TT/FF 25.1/24.1 | kit repo | paper FAIL
- dsfd_qbank_N x864: NEEDS RE-RUN | rec SS 248.61 (TT 332.23) FF 1.58 spread TT/FF 2.8/3.1 | kit repo | paper PASS
- dsfd_qbank_S x864: NEEDS RE-RUN | rec SS 69.7 (TT 214.61) FF 21.41 spread TT/FF 12.8/13.1 | kit repo | paper PASS
- dsfd_rstg x216: NEEDS RE-RUN | rec SS 228.33 (TT 328.42) FF 30.99 spread TT/FF 1.2/1.4 | kit repo | paper PASS
- ot_s81_cfg7_seq x864: NEEDS RE-RUN | rec SS 119.66 (TT 321.2) FF 25.53 spread TT/FF 12/11.3 | kit repo | paper PASS
- ot_s81_cfg7_seq_bfp x228: NEEDS RE-RUN | rec SS -24.67 (TT 244.26) FF 23.88 spread TT/FF 14.4/13.5 | kit repo | paper FAIL
- ot_s81_sstn_base566 x660: NEEDS RE-RUN | rec SS 232.82 (TT 329.25) FF 24.82 spread TT/FF 14.5/14.5 | kit repo | paper PASS
- ot_s81_sstn_payload536 x660: NEEDS RE-RUN | rec SS 255.69 (TT 344.2) FF 26.61 spread TT/FF 8.8/9 | kit repo | paper PASS
- ot_s81dv_xfin x16: NEEDS RE-RUN | rec SS -345.05 (TT 4.78) FF 11.46 spread TT/FF 57.8/56.2 | kit repo | paper FAIL
- ot_s81sl_capc5r x16: NEEDS RE-RUN | rec SS 185.74 (TT 326.69) FF 13.38 spread TT/FF 0/0 | kit repo | paper PASS
- ot_s81sl_eg x16: NEEDS RE-RUN | rec SS -294.79 (TT 71.85) FF 16.24 spread TT/FF 10.1/10.6 | kit repo | paper FAIL
- ot_s81sl_xrt1 x15: NEEDS RE-RUN | rec SS -238.75 (TT 40.44) FF 9.45 spread TT/FF 69.1/64.5 | kit repo | paper FAIL
- ot_s81sl_xrt3 x1: NEEDS RE-RUN | rec SS -304.84 (TT 9.5) FF 10.86 spread TT/FF 64.1/54.4 | kit repo | paper FAIL
- ot_v41_bf_col x456: NEEDS RE-RUN | rec SS -221.99 (TT 63.59) FF 6.24 spread TT/FF 44.4/32.6 | kit NOT IN REPO | paper FAIL
- ot_v41_rom_elem_q_qxpq_w10 x864: NEEDS RE-RUN | rec SS -182.29 (TT 116.28) FF 12.25 spread TT/FF 50.2/38.2 | kit NOT IN REPO | paper FAIL

### s81_head: 3 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 3 (paper FAIL 1, paper PASS 1)
- ot_dsrom_head_elem x1320: NEEDS RE-RUN | rec SS 133.67 (TT 133.67) FF 10.81 spread TT/FF -/- | kit NOT IN REPO | paper INCOMPLETE
- ot_s81hd_spo x6: NEEDS RE-RUN | rec SS -70.45 (TT 19.69) FF 40.87 spread TT/FF 78/72.9 | kit repo | paper FAIL
- ot_s81hd_spr x6: NEEDS RE-RUN | rec SS 223.93 (TT 373.03) FF 32.35 spread TT/FF 48.3/44.9 | kit repo | paper PASS
- surviving routed runs signed (pathfinding, pre-4b7b2b3e64 kits): dsdv_eng_rr_h0 NOT SIGNED (SS -396.55/5108 ep, FF std -20.76, TT +8.05 = ORFS exactly, face_guard shared 68, sdc_lint 2), dsdv_eng_rr_h1 NOT SIGNED (SS -377.41, FF -32.70, TT +13.90); CP1 r10a col_h10_r1__t1 NOT SIGNED (SS -462, FF std -45.7 (raw +0.6), TT -212, face_guard dropped 120)

## hc batch C (sub-agent)
- 2026-10-24 08:19 PDT start: batch C = dsfd_cfifo_crs4 (kit s81coll_cfifo_crs4 = plan LEF; crs4p NOT used), dsfd_node_{LLd,LLfd,LLfu,NNfd,NNfu} (s81net_node_*), dsfd_rstg (s81net_rstg); run base /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/ (epyc2/epyc3), src = git archive origin/main fd219eafe7

## SIGNOFF re-signoff list v3 — TT RULE (2026-10-24 08:22 PDT, main f942bf2f72; supersedes v1/v2 above)
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).

### s81: 37 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 37 (paper FAIL 1, PASS 35, no/incomplete record 1)
- dsdv_bk_g x1: NEEDS RE-RUN | rec TT 17.77 FF 6.59 spread TT/FF 67.5/59.6 | kit repo | paper PASS
- dsdv_bksel_c x1: NEEDS RE-RUN | rec TT 54.58 FF 8.99 spread TT/FF 51.6/48.5 | kit repo | paper PASS
- dsdv_bksel_q x4: NEEDS RE-RUN | rec TT 37.37 FF 5.16 spread TT/FF 65.9/61.2 | kit repo | paper PASS
- dsdv_eng_tap x15: NEEDS RE-RUN | rec TT 38.55 FF 22.75 spread TT/FF 24.8/23.3 | kit NOT IN REPO | paper PASS
- dsdv_eng_tap_w x1: NEEDS RE-RUN | rec TT 76.26 FF 19.93 spread TT/FF 21.9/21 | kit NOT IN REPO | paper PASS
- dsdv_gunit_l0 x1: NEEDS RE-RUN | rec TT 198.78 FF 5.63 spread TT/FF 58.2/55.6 | kit repo | paper PASS
- dsdv_gunit_l0r x1: NEEDS RE-RUN | rec TT 24.55 FF 24.06 spread TT/FF 12.5/12.6 | kit repo | paper PASS
- dsdv_gunit_l1 x1: NEEDS RE-RUN | rec TT 59.31 FF 2.71 spread TT/FF 76/73.7 | kit repo | paper PASS
- dsdv_gunit_l1c x1: NEEDS RE-RUN | rec TT 0.11 FF 16.71 spread TT/FF 36.2/36.3 | kit repo | paper PASS
- dsdv_gunit_l2 x1: NEEDS RE-RUN | rec TT 74.7 FF 4.99 spread TT/FF 48.9/47.3 | kit repo | paper PASS
- dsdv_gunit_l3 x1: NEEDS RE-RUN | rec TT 133.72 FF 10.01 spread TT/FF 61/58.5 | kit repo | paper PASS
- dsdv_gunit_l4 x1: NEEDS RE-RUN | rec TT 71.87 FF 5.94 spread TT/FF 52.8/52 | kit repo | paper PASS
- dsdv_gunit_l4r x1: NEEDS RE-RUN | rec TT 144.14 FF 18.96 spread TT/FF 10.6/10.1 | kit repo | paper PASS
- dsdv_gunit_l5 x1: NEEDS RE-RUN | rec TT 20.6 FF 20.07 spread TT/FF 101.9/95.3 | kit repo | paper FAIL (recorded TT pin-flop spread 101.9 ps > 80; recorded FF pin-flop spread 95.3 ps > 80)
- dsdv_gunit_l5f x1: NEEDS RE-RUN | rec TT 151.76 FF 22.01 spread TT/FF 11.4/11 | kit repo | paper PASS
- dsdv_idx_tx_n32 x1: NEEDS RE-RUN | rec TT - FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD (no closed record in the repo)
- dsfd_bf_front_roots x228: NEEDS RE-RUN | rec TT 0 FF 18.2 spread TT/FF 9.9/8.4 | kit NOT IN REPO | paper PASS
- dsfd_cfifo_crs4 x72: NEEDS RE-RUN | rec TT 40.3 FF 11.34 spread TT/FF 61.3/60.6 | kit repo | paper PASS
- dsfd_node_LLd x72: NEEDS RE-RUN | rec TT 95.22 FF 23.29 spread TT/FF 12.8/13.1 | kit repo | paper PASS
- dsfd_node_LLfd x504: NEEDS RE-RUN | rec TT 89.29 FF 18.49 spread TT/FF 13.1/12.7 | kit repo | paper PASS
- dsfd_node_LLfu x516: NEEDS RE-RUN | rec TT 84.29 FF 22.89 spread TT/FF 16.3/17.1 | kit repo | paper PASS
- dsfd_node_NNfd x516: NEEDS RE-RUN | rec TT 100.18 FF 16.83 spread TT/FF 14.2/14.3 | kit repo | paper PASS
- dsfd_node_NNfu x504: NEEDS RE-RUN | rec TT 90.08 FF 12.49 spread TT/FF 25.1/24.1 | kit repo | paper PASS
- dsfd_qbank_N x864: NEEDS RE-RUN | rec TT 332.23 FF 1.58 spread TT/FF 2.8/3.1 | kit repo | paper PASS
- dsfd_qbank_S x864: NEEDS RE-RUN | rec TT 214.61 FF 21.41 spread TT/FF 12.8/13.1 | kit repo | paper PASS
- dsfd_rstg x216: NEEDS RE-RUN | rec TT 328.42 FF 30.99 spread TT/FF 1.2/1.4 | kit repo | paper PASS
- ot_s81_cfg7_seq x864: NEEDS RE-RUN | rec TT 321.2 FF 25.53 spread TT/FF 12/11.3 | kit repo | paper PASS
- ot_s81_cfg7_seq_bfp x228: NEEDS RE-RUN | rec TT 244.26 FF 23.88 spread TT/FF 14.4/13.5 | kit repo | paper PASS
- ot_s81_sstn_base566 x660: NEEDS RE-RUN | rec TT 329.25 FF 24.82 spread TT/FF 14.5/14.5 | kit repo | paper PASS
- ot_s81_sstn_payload536 x660: NEEDS RE-RUN | rec TT 344.2 FF 26.61 spread TT/FF 8.8/9 | kit repo | paper PASS
- ot_s81dv_xfin x16: NEEDS RE-RUN | rec TT 4.78 FF 11.46 spread TT/FF 57.8/56.2 | kit repo | paper PASS
- ot_s81sl_capc5r x16: NEEDS RE-RUN | rec TT 326.69 FF 13.38 spread TT/FF 0/0 | kit repo | paper PASS
- ot_s81sl_eg x16: NEEDS RE-RUN | rec TT 71.85 FF 16.24 spread TT/FF 10.1/10.6 | kit repo | paper PASS
- ot_s81sl_xrt1 x15: NEEDS RE-RUN | rec TT 40.44 FF 9.45 spread TT/FF 69.1/64.5 | kit repo | paper PASS
- ot_s81sl_xrt3 x1: NEEDS RE-RUN | rec TT 9.5 FF 10.86 spread TT/FF 64.1/54.4 | kit repo | paper PASS
- ot_v41_bf_col x456: NEEDS RE-RUN | rec TT 63.59 FF 6.24 spread TT/FF 44.4/32.6 | kit NOT IN REPO | paper PASS
- ot_v41_rom_elem_q_qxpq_w10 x864: NEEDS RE-RUN | rec TT 116.28 FF 12.25 spread TT/FF 50.2/38.2 | kit NOT IN REPO | paper PASS

### s81_head: 4 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 4 (paper FAIL 0, PASS 2, no/incomplete record 2)
- ot_s81hd_elemA_cv x1056: NEEDS RE-RUN | rec TT - FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD (no closed record in the repo)
- ot_s81hd_elemB_cv x264: NEEDS RE-RUN | rec TT - FF - spread TT/FF -/- | kit NOT IN REPO | paper NO RECORD (no closed record in the repo)
- ot_s81hd_spo x6: NEEDS RE-RUN | rec TT 19.69 FF 40.87 spread TT/FF 78/72.9 | kit repo | paper PASS
- ot_s81hd_spr x6: NEEDS RE-RUN | rec TT 373.03 FF 32.35 spread TT/FF 48.3/44.9 | kit repo | paper PASS
- surviving routed runs (TT rule): dsdv_eng_rr_h0 NOT SIGNED (TT +8.05 PASS; FF hold std -20.76 / raw -6.27; sdc_lint 2; face_guard shared 68), dsdv_eng_rr_h1 NOT SIGNED (TT +13.90; FF -32.70 / raw -6.41); CP1 r10a col_h10_r1__t1 NOT SIGNED (TT -212.39, FF -45.74, 1278 slew viol TT, face_guard dropped 120)
- 2026-10-24 08:24 PDT reviews written /srv/opentallas-scratch/claude/elem-s81/hc/reviews/<kit>.json (crs4 + 5 nodes PASS-COND: no pre-route images for nodes / crs4 spread margin; rstg PASS); 7 jobs (bench+route+collect via hc/C/tools/cl_local.py = closure-loop ref_tile env reproduced) queued: ot-run --hosts epyc2,epyc3 (both memory-full: 20+ waiters each); local client logs hc/C/logs/<kit>.log

## hc batch A (gunit) (sub-agent)
- 2026-10-24 08:25 setup: main fd219eafe7 snapshots per kit at /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/src (localhost: l5_n32 l4 l1c l0r l4r l5f; epyc3: l0 l1 l2 l3); runner hc/bin/route_kit.sh (closure_loop route-stage env reproduced: TC, mm hold + FF SDCs + io_ref_routed, pinflop ref, fp-lint/preroute gate, LEC-off shim).
- 2026-10-24 08:25 reviews (hc/reviews/*.json): l0r PASS; l0 l1 l1c l2 l3 l4 l4r l5f PASS-COND (l1 spread 76/80 margin, l1c TT +0.11 record). dsdv_gunit_l5: FIX = route kit dsdv_gunit_l5_n32 (@1766568f0, 25 sources byte-identical to main; main's parent binds it since 127356adf2, inventory cl_latest = n32 job); the g3 kit (101.9 ps spread) is stale vs main RTL. n32 gate pin-flop spread TT 44.8.
## 08:40 head ft-only kits: 8 placed + reviewed (hd_turn_a/b, hd_st_turn/str/n3/n4/m/k5: FACE_GUARD PASS, reg-reg>750 = 0,
  pin->reg p90 6.7-8.0 um, dens <= 0.08) -> results/geom_review/s81_head_g3_*.json (branch 325c24668d); routing at 36 GB on
  epyc3/localhost (kits_head/launch.log). hd_spn/spn_end/serdes/lep0N/mesh/ctl/host BLOCKED on plan sources (posted S81-HEAD).
- slice_station t7 OOM at 28 GB in 6_report (peak 29.3 GB) -> watcher retries at 56 GB.
- 2026-10-24 08:27 PDT attempt 1 of rstg/nnfd/nnfu FAILED at 3_3 global place (flow infra, not design): my minimal source snapshot lacked physical/dsrom_window_source/leaf_iohold.tcl (OT_IOHOLD_IN hook). Snapshot now = tools rtl Makefile + all physical/* except ref_tile (only my 7 kits) at fd219eafe7; relaunched as attempt 2 (failed dirs kept as <kit>.failed_a1.*). Bench judge fixed to closure_loop expected_fail_seen (fail_regex decides; rstg mutant was CAUGHT, my first judge mis-read rc 0)

## hc batch D (sub-agent)
- 2026-10-24 08:27 setup: snapshot origin/main fd219eafe7 -> per-kit trimmed src (tools rtl physical Makefile minus other ref_tile kits + job extra results paths) at /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/src on localhost, synced to epyc2/epyc3. Runner hc/D_bin/run_stage.sh (closure_loop launch_stage reproduction: TC corner, mm hold, pinflop ref, fp-lint/preroute gate, LEC-off docker shim). Installed missing ~/.local/opentallas-pdk-asap7 on localhost (copy of epyc2's). New fix kit s81hd_spo_m4 (216x216 compact, same fix as spr_m -> spr_m4; spo_m rec spread 78/72.9, ins 708 ps, TT +19.7) generated in hc/s81hd_spo_m4/src (not committed); spo_m re-run in parallel as recorded.

## GEOM-REVIEW findings (2026-10-24 09:35 PDT)
- Frames col_h9_r0_p2/p4/p5/p6 and col_h10_r0_p4 (floorplan only, not placed): **FAIL on inputs** (results/geom_review/col_*__{g3k2|elem}_col_*__<hash>.json; images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81F/<kit>/ (see col_h9_r2__t1/h9_r2_dataflow.png)). Same generator defects as S81's 7 frames (S81.md 09:35): ROM ot_rom_4096x72_m8 cores have no lib (untimed, unbuffered address fan-out); elem_q/bf_col cores (552/645 ps internal latency) on ordinary grid taps; sequencer at the row end. Stop these frame runs until the plan/generator fix lands.
- DISK RULE: col_h9_r0_p5/p6 run from intel2:/srv/opentallas-scratch/claude/elem-s81, which is on intel2's ROOT disk (/dev/nvme1n1p2 /). Use /srv/opentallas-scratch2/claude/ there.
- slice_station kits: tile review in progress.

## hc batch B (sub-agent)
- 2026-10-24 08:29 reviews written (hc/reviews/<kit>.json: eg PASS, 7 PASS-COND, 0 FAIL). dsdv_bksel_q: inventory kit s81dvbk_sq_hq3 never closed; its views are the hk2l closure (9da51c5d14) -> re-run kit s81dvbk_sq_hk2l. Main RTL differs from closure source for selc2/hk2l/xfin(ENG mode, never gated)/capc5r/xrt1 -> benches re-run. Snapshots main fd219eafe7 under /srv/opentallas-scratch/claude/elem-s81/hc/<kit> (epyc2: /srv/opentallas-scratch2/...).
- 2026-10-24 08:29 routes running (ORFS synth/floorplan): epyc3 l0 (detached after ot-run cancel); intel2 l5_n32 l4 l1c l0r l4r; intel1 l5f l1 l2 l3 (localhost/epyc2/epyc3 had no memory admission: 19+ waiters each; intel1/2 used, run dirs /srv/opentallas-scratch/claude/elem-s81/hc/<kit> -> scratch2). l5_n32 bench running intel2. signoff tools = main a2c726e597 (TT-rule signoff.py 70c11a4b18).

## CODEX notes

08:59 PDT: Collected bulk terminal failures:20 kit logs exit137 (includes5 blocked frames),8 head ft logs exit137. Docker events show explicit SIG15/SIG9 on unrelated jobs at08:34, kernel OOM absent; do not label all OOM.23 valid terminal station/head routes resumed from isolated checkpoint copies in <host>:/srv/opentallas-scratch{2}/claude/codex-s81/stations/<type>, clients/logs localhost:/srv/opentallas-scratch/claude/codex-s81/*.resume.log. Existing other running jobs left alone. Synth-ODB face_guard +face_keep/release installed; signoff final. t7 reserves56GB (prior measured29.3GB), others36GB. Review contact sheets inspected; t23 FAIL133 data paths >750um,max780 -> held for placement correction. All other placements sparse/no macros, zero>750, reviewed PASS-COND. Capc5r bench PASS3 baseline checks +3 mutants CAUGHT.

09:50 PDT CODEX: 32revised405um slice_station routes startedepyc2/intel1 scratch2.../codex-s81/station405,40GB8threads. t7ROOTowned,t19empty/noFTNOTRUN. LatestROOTfoundclockportsenterdataIOconstraints(SDCobject-vs-nameregexpbug); startedroutesare nowdiagnosticpendingSDCfix/regeneration. Newsubmissionshelduntilfix.

10:29 PDT CODEX: 32macrofree reach405/canonicalSDC/nativeMMkits runningepyc2/intel1 scratch2.../codex-s81/station405_c1,clients1994756..1994788,40GB8threads. 30admitted/2pending at10:29; excludesROOTt7+emptyt19. Reviewed32geometries beforelaunch. Old400/750reach+badSDCresults preserveddiagnostics. All12frames remainheld forFTsite/congestionreview despiteROMlib/earlyclock/seqcenter improvements.

## CODEX complete core inventory (11:05 PDT)

32 native legacy core designs plus l5_n32 (33 total); no old PASS is SIGNED. Canonical clock/IO/native-corner migration is required before repeating old runners (770ps, legacy hold contract, mixed WC/BC, absent canonical face gate).

| Core | Host | Result / setup ps / hold ps | Next |
|---|---|---|---|
| dsdv_gunit_l0 | epyc3 | not_met / 12.438 / -137.679 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l0r | intel2 | not_met / -50.059 / -79.725 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l1 | intel1 | not_met / -150.537 / -148.711 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l1c | intel2 | not_met / -81.545 / -69.166 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l2 | intel1 | not_met / 27.468 / -129.59 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l3 | intel1 | not_met / 64.119 / -101.401 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l4 | intel2 | not_met / 7.329 / -147.692 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l4r | intel2 | not_met / 73.229 / -25.245 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l5f | intel1 | not_met / 89.626 / -46.784 | Canonical rekit; native data-port guard first |
| s81_sstn_base566 | epyc2 | not_met / 53.761 / -9.554 | Canonical rekit; native data-port guard first |
| s81_sstn_payload536 | epyc2 | not_met / 47.419 / -33.04 | Canonical rekit; native data-port guard first |
| s81coll_cfg7_seq_bfp_pr | epyc2 | not_met / 57.884 / -24.942 | Canonical rekit; native data-port guard first |
| s81coll_cfg7_seq_pr | epyc2 | not_met / 41.617 / -31.544 | Canonical rekit; native data-port guard first |
| s81coll_cfifo_crs4 | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dv_xfin | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_g2 | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_selc2 | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_sq_hk2l | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81fill2_qbank_n | epyc2 | pass / 69.316 / 15.293 | Canonical rekit; native data-port guard first |
| s81fill2_qbank_s | epyc2 | pass / 8.633 / 19.241 | Canonical rekit; native data-port guard first |
| s81hd_spo_m | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81hd_spo_m4 | epyc3 | not_met / -53.749 / -113.622 | Canonical rekit; native data-port guard first |
| s81net_node_lld | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_llfd | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_llfu | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_nnfd | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_nnfu | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_rstg | epyc3 | pass / 254.786 / 164.122 | Canonical rekit; native data-port guard first |
| s81sl_capc5r | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_eg | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_xrt1 | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_xrt3_b | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| dsdv_gunit_l5_n32 | - | NOT COLLECTED / - / - | Cancellation/source collection; canonical rekit |

Structural gaps and exact next actions:

- LOST monolithic VP view: Old closed_archive vp LEF no longer readable; author design replaces VP with16hcpl lanes+2stores and36ksoftlogic, so do not fabricate lostview. Use S81-CORES staged atomicVP lane/store mapping; retain boundary/bundle geometry gate; no physical closure until namedchildrenSIGNED.
- 74 leaf plan types: Main still has VE460279cell/no real closedview andresidual475279>400000; authorbranchatomicmap mayreduceG0C butusesre-pinnedVS/VQstubviews. Finish VQ/hrow/VS ports; read-only staged geometry167linevariantpatch at~/wt/s81-cores. Existing buswindow->fixedVS/VQdistances>750in46/74types,max1312; require perbus placement orRTLrelay+pricedcycles beforeleafP&R.
- 16svc plan types: Mainmapstale:64hdp+16hgrp views absent there; author S81-CORES uses64ot_s81c_attn_hcore reviewedGR8 plus8re-floorplannedhrow, residual247k/80k. Finish hrow uniform gate; transplant exactauthorhardcoredeclarations+sourcefiles on own integration afterreviewedactualviews; retain2FTslotlatencyincrements andrecompute405reach beforeG3.
- engine plan type: Mainmonolithicdsdv_eng_rr418942cells has no LEF andover400kcap; author usesE/H0/H1 split reviewedGR8. Integrate actual split source/LEF/pins/views afternativeuniformSIGNED checks; current monolithic kit cannotroute.
- VS repin: Real face_guard violations130dropped,989shared,259feedthrough; OT_KEEP_PIN_REGS+post-synthpin_reg_splitpathfindingdoesnotrepairpre-routeRTLboundarycontract. Duplicate same-edge outputportflops beforeYosysmerge andkeep captures ofunusedinputs; bitexactRTL/netlistlockstep+mutant required beforephysicalretry. No waiver/no unchanged rerun.
- eng_tap / eng_tap_w: No standalone ref_tile kit inrepo; svc integration child sources need extractedwrapper/pincontract. Extract from actualsvc hierarchy/bind source beforeattemptingkit; no guessedclock/pin model.
- frame12types: 434ROMTT/FF libs+74earlytaps+13rowsequencers correctedmain; wideFT1105-bit common-site grids cannotfit43umWstrip under405reach. Consume HBMRowAllocator full-bitrowlegal sites inisolatedframekit; exactpairedhop<=405 gate andpricedFTcounts beforeGRT.
- macro-free slice_station__t19: Emptyzero-celltype,noFTslots; no physical job appropriate. Declare dark/nonphysicaltype treatment incurrentplan completeness contract; do not synthesize emptyfabric asclosedmacro.


CODEX 2026-10-24 11:24 PDT: Station405c1 first11uniformgates NOTSIGNED: setupinput-16..-54ps +DRVs86..580; FFholdsubset-2..-18ps, allDRC0/ant0 andspread31..60PASS. t34 additional2060mergedfaceFFs needsRTLboundarydiagnosis. t9/25/27 resetrecoveryprebalance loops known; otherjobsstillroute/RCX. No unchangedwholewave retry. Legacy33core inventory earlier explicit, L5benchgap recovered nowpositivePASS/mutantsCAUGHT.
- 2026-10-24 12:19 STOPPED per ELEM-S81 order: Codex's legacy-runner re-runs came back not_met (FF hold -25..-148 under the standard), and a canonical native TT/FF rekit comes first. Cancelled the l5_n32 route on intel2 (client 1715759; containers serene_swanson and a respawned determined_elbakyan stopped). The other 9 routes had already finished rc=0. Their raw kit-SDC corner_sta (legacy contract, NOT signoff.py) is TT/FF/DRC: l0 +140.1/+4.1/0, l0r +13.3/+28.4/0, l1 +62.6/+6.4/0, l1c -18.2 (9 ep)/+9.5/0, l2 +90.8/+5.3/0, l3 +127.5/+14.4/0, l4 +70.7/+9.5/0, l4r +136.6/+22.7/0, l5f +153.0/+18.5/0. signoff.py NOT RUN. l5_n32 bench: lint and gunit exact PASS, mut8/mut10 caught; sinkhorn_fs_eq + its 2 mutants NOT RUN (script rtl/hdc/v41/test/run_sinkhorn_fs_eq.sh is absent on main) -> bench FAIL as a stage. Run dirs left in place under hc/<kit>.

## RESUMED 12:15 PDT (Claude, after the 08:50-12:04 limit). Adopted from Codex (handoff codex_s81_to_claude_20261024_reset.md):
  station405_c1 (epyc2+intel1 scratch2, 18 live at 12:04), BK drain full-layer build (epyc3 codex-s81/bk_drain_layer),
  head abstract PSM c2 (intel2 codex-s81/trial_head_psm_c2). Root keeps t7 r4d (codex-clock), CP1 col_h10_r0_p1 and the KV hub.
- CANCELLED my old v4.8 (pre-face_keep, pre-405) station routes t4 t8 t9 t10 t22 t24 t25 t27 t29 t32: superseded by station405_c1.
  Stopped retry_watch. The 5 frame routes were already dead (exit 137 at 08:30; GEOM-REVIEW FAIL, S81 owns the frame generator fix).
  Head ft-station routes died at 08:34; Codex resumed them (codex-s81/hd_st_*.resume.log).
- hc batches: B/C/D/bind48 sub-agents died at the limit. Batch A (legacy gunit runner) STOPPED: Codex's 33-core inventory shows the
  legacy runners all fail FF hold, so a canonical rekit comes first.
- DISK (COORD 12:1x): localhost elem-s81 pruned 492 -> 143 GB (freed ~349 GB: stage ODBs 1-5/6_1, def/gds, objects, src snapshots of
  dead runs). epyc2 ROOT-disk hc dir (104 GB, dead batch C/D runs, nothing live) removed after saving logs to
  localhost elem-s81/hc_epyc2_logs. intel2 root-disk kits (37 GB) moved to /srv/opentallas-scratch2 (symlinked). From now on: scratch2 only on intel/epyc2.
- SIGNOFF ROM-lib question answered in SIGNOFF.md: elem_q/bf_col specs carried ROM tt/ff/ss libs; run-level is unverifiable (DBs lost), so UNVERIFIED.
- 12:40 adopted-job check: the BK drain build on epyc3 is still in Verilator (obj/ growing, build.log 12:21). The head PSM c2 on intel2 is still in VDD IR (no result). Both are left running.
- 12:40 sub-agents launched: (1) signoff.py tt,ff on the 9 finished legacy gunit routes (no new P&R); (2) station405_c1 adopt,
  collect, signoff, root-cause and fix on branch claude/elem-s81-st405-1024; (3) canonical rekit of the legacy cores on the VQ r12 recipe,
  branch claude/elem-s81-cores-1024. Merged my branch to main e7c09034ae (42 G3 review JSONs).

## gunit signoff (sub-agent)
- 2026-10-24 12:2x PDT: launched signoff.py (main e7c09034ae snapshot at hc/_main/src on epyc3/intel1/intel2) on the 9 finished gunit routes via ot-run (localhost client logs ~/coord/tmp_s81_gunit_so/<kit>.log); out = hc/<kit>/signoff_tt_ff. Results to follow.

## GEOM-REVIEW findings (2026-10-24 13:10 PDT, tile)
- 34 v4.8 slice_station kits (GR-S81S, 4_cts snapshots 08:14): 29 PASS-COND, 5 FAIL = t3, t4, t9, t25, t32 (1104-b E-W slots across 1443 um with 2 stations = 721-um hops on M4-M7, reg2out at placement already ~0). FAIL kits: do not route as is; 3 stations (481 um) or the 405c1 resize. All kits: in2reg setup -8..-24 ps because station-0 sinks at 215-240 ps insertion < ~250 needed -> pad trees so MIN station-0 insertion >= 250 ps; judge hold at FF signoff. Records results/geom_review/slice_station__t*__*.json (main 410d3d1712). station405c1 kits being reviewed now.
- 2026-10-24 12:45 PDT RESULT: signoff.py (main e7c09034ae) RAN on all 9 (ot-run, rc=1 = NOT SIGNED, sessions completed; TT+FF, SPEF). **0/9 SIGNED.** Records: <host>:hc/<kit>/signoff_tt_ff/signoff.json.
  | kit (host) | TT setup WNS | FF hold WNS (= hold_ff_sdc) | spread TT/FF | slew viol TT/FF | face_guard | verdict: failing checks |
  |---|---|---|---|---|---|---|
  | l0 (epyc3) | +140.05 | -22.34 (234 ep) | 48.6/46.6 | 3/2 | FAIL dropped144 shared41 | hold_ff, drv, face_guard, sdc_lint |
  | l0r (intel2) | +13.27 | +6.89 | 11.5/11.6 | 0/0 | FAIL shared1 | face_guard, sdc_lint |
  | l1c (intel2) | -18.21 (1 ep) | -16.26 (140) | 51.2/50.2 | 1/1 | FAIL dropped16 shared2 | setup_tt, hold_ff, drv, face_guard, sdc_lint |
  | l4 (intel2) | +70.66 | -16.44 (591) | 45.6/45.6 | 0/0 | FAIL shared66 | hold_ff, face_guard, sdc_lint |
  | l4r (intel2) | +136.56 | +9.09 | 7.9/8.4 | 0/0 | FAIL shared1 | face_guard, sdc_lint |
  | l1 (intel1) | +62.62 | -20.66 (496) | 73.3/70.7 | 2/1 | FAIL dropped80 shared353 | hold_ff, drv, face_guard, sdc_lint |
  | l2 (intel1) | +90.80 | -20.74 (276) | 58.6/56.6 | 11/8 | FAIL shared552 | hold_ff, drv, face_guard, sdc_lint |
  | l3 (intel1) | +127.45 | -11.64 (252) | 42.1/41.0 | 0/0 | FAIL shared107 | hold_ff, face_guard, sdc_lint |
  | l5f (intel1) | +152.96 | +7.69 | 15.2/14.0 | 0/0 | PASS | sdc_lint only |
  All: unconstrained 0, cap viol 0, DRC 0 / antenna 0, spread <= 80 PASS. sdc_lint FAIL everywhere = the known ref_tile Tcl-program SDC issue (parse/forbidden-command fail-closed + period 833.333 vs plan 833), not a timing finding.
  CAVEATS: (1) the standard boundary-hold overlay was NOT applied ("OVERLAY skipped vclks 0": ref_tile SDCs have no IO virtual clock), so hold_ff = the raw signoff.sdc hold (its own OT_BH die budget). (2) FF hold is 25-27 ps worse than the route's corner_sta (l0 +4.14 -> -22.34, same worst-path class input->pin-flop) because corner_sta read 6_final.sdc first (set_input_transition 150 ps on every input, set_load) and the bare signoff.sdc has neither: faster input slews -> less hold margin. TT setup matches corner_sta exactly.
  Closest to SIGNED: l5f (sdc_lint form only), l0r/l4r (+1 shared face_guard bit each). The 6 others need hold repair at FF and RTL boundary fixes (face_guard).

## GEOM-REVIEW findings (2026-10-24 13:40 PDT, tile batch 2, main da5213b0b3)
- station405c1: t3/t9/t25 (5_1_grt) PASS-COND: the v4.8 FAIL is fixed (1104-b E-W slots now 4 stations, hops 357-363 um, GRT overflow 0). t33 (N-S, 6_final) PASS-COND: hops 302-310 um but NOT SIGNED (TT -25.9, FF hold -45, spread 86.75 > 80, 1830 slew: one BUFx6f per 300-360-um hop is too weak; use a stronger/2-stage repeater). All 32 kits match frame_ft405_explicit_candidate.json, worst sampled hop 391 um. t4/t32 NOT REVIEWED (no ODB: ot-run no host qualifies).
  Common conditions: reset recovery -550..-578 ps (single arst_n to per-tap syncs, see OWNER? in GEOM-REVIEW lane), input -> station-0 hold -118..-148 ps at TT (judge hold at FF signoff; fix station-0 insertion >= 250 ps as before).
  Images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-B2/slice_station__t{3,9,25,33}_405c1/; records results/geom_review/slice_station__t*__station405c1_*.json

## canonical cores (sub-agent)
- 2026-10-24 12:35 PDT: branch claude/elem-s81-cores-1024 (wt localhost:/srv/opentallas-scratch/claude/wt/elem-s81-cores) c111758856: physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py = VQ r12 recipe (gen_kit_repin @57d58e1307) on plan hard-core pins + ref_tile specs + typed clk/rst context + post-GRT DRV pass. 29/31 kits generated (bksel_q, capc5r refused: hard children unsigned). Stage 1 (synth + face_guard + place, for the review render) launched via ot-run on all 29: run root <host>:/srv/opentallas-scratch/claude/elem-s81-cores/r1/<kit>, logs localhost:.../elem-s81-cores/logs/.

## OWNER? (13:50) ft seam budget split (station405 sub-agent analysis)
- FT_HOP_IN_SHARE = 0.08 T (COORD 10-23 15:39) leaves the station-0 flops a combined TT-setup + FF-hold window of about +3 ps, at I_TT = 250
  (setup + hold = 0.2*I_TT - 42 - (dTT - dFF)). Any CTS spread among station-0 flops (20-35 ps measured) therefore fails setup on the
  early flops or hold on the late ones. This matches station405_c1 (t2 -54.6/-12, t13 -31.7/-9.1, t21 -45/-2.8, t15 -16.4/-2.5) and T7 r4d (TT -6.99 / FF -0.30).
  Padding station-0 insertion only moves the failure to FF hold.
- PROPOSAL: re-split the seam to receiver 0.16 T (ft input delay max 0.84 T, output delay max 0.16 T). Period, uncertainty and the hold
  overlay stay unchanged. Sender evidence: worst ft reg2out slack across 17 finished station tiles >= +245.9 ps, so it stays >= +179.
  This must be DIE-WIDE: frames' ft ports must use the same share. Plan field clock.ft_hop_in_share (default 0.08 = unchanged).
- Meanwhile: variant A (0.08, in-contract fixes: SLEW_MARGIN for the RCX/setRC slew gap, FF-only hold repair, current tap_balance)
  and variant B (0.16, labelled CANDIDATE, not a closure until ruled) run in parallel. Needs COORD/owner + S81 (frames) decision.

## COORD RULING 2026-10-24 13:55 PDT: ft seam split 0.16 T receiver share APPROVED (die-wide, S81)
- clock.ft_hop_in_share = 0.16 for S81: ft input delay max 0.84 T, output delay max 0.16 T. Period, uncertainty and hold
  overlay unchanged. This re-divides an internal interface budget; the clock is NOT relaxed.
- Conditions: (1) frames and stations switch TOGETHER (S81 owns the plan field + frame SDCs); (2) sender reg2out slack
  is re-checked on every station/frame kit at the new 0.84 T (re-run signoff only, no re-route needed where slack >= 0);
  (3) DIE-STA/DIE-CI seam STA on real views is the final word: if a real seam fails at 0.16, the ruling is revisited.
- Variant B results now count as closure candidates under this ruling; variant A may stop when B signs.
