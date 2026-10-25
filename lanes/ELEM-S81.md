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

## COORD RULING 2026-10-24 12:37 PDT: ft seam split 0.16 T receiver share APPROVED (die-wide, S81)
- clock.ft_hop_in_share = 0.16 for S81: ft input delay max 0.84 T, output delay max 0.16 T. Period, uncertainty and hold
  overlay unchanged. This re-divides an internal interface budget; the clock is NOT relaxed.
- Conditions: (1) frames and stations switch TOGETHER (S81 owns the plan field + frame SDCs); (2) sender reg2out slack
  is re-checked on every station/frame kit at the new 0.84 T (re-run signoff only, no re-route needed where slack >= 0);
  (3) DIE-STA/DIE-CI seam STA on real views is the final word: if a real seam fails at 0.16, the ruling is revisited.
- Variant B results now count as closure candidates under this ruling; variant A may stop when B signs.

## From S81 (2026-10-24 13:05 PDT): ft seam split 0.16 is on main 90fd169e93
clock.ft_hop_in_share = 0.16 in physical/die_plan/s81/die_plan.json (+ gen_plan_v4.py); gen_phys.sdc / sdc_lint floors / die_ci
kit_budget read it (default 0.08 for other dies). Regenerate station kits from main (gen.py phys) to get 0.84 T ft_i / 0.16 T ft_o;
your variant-B SDCs should match these byte for byte in the ft lines. Frame kits (S81 g3k4) switch at the same plan sha.

## station405 (sub-agent)
- 12:50 st405: inventory of 32 station405_c1 types: 17 finished (t1 t2 t11 t12 t13 t15 t16 t17 t20 t21 t23 t24 t28 t30 t31 t33 t34), 15 live (t3 t5 t6 t8 t9 t10 t14 t18 t22 t24.. in DRT; t27 in GRT reset-recovery repair -207), t4/t32 NOT RUN (ot-run race). Re-signoff with main e9367f5c (KIT/signoff_main_e9367f5c, old KIT/signoff kept): 16/17 NOT SIGNED, t13 rerun. t34 face_guard now PASS (2060 merged was the false positive).
- root causes: (1) DRV: repair_design repeaters ~190-196 um on ASAP7 setRC, RCX slew 1.8x (worst 438..587 ps on EVERY tile, 86..1830 violators = counts not slews) -> SLEW_MARGIN 50 / CAP_MARGIN 20. (2) TT in2reg setup vs FF hold: at ft share 0.08 T the station-0 window is ~3 ps (setup+hold = 0.2*I_TT - 42) -> COORD approved 0.16 T die-wide (plan clock.ft_hop_in_share; S81 owns the plan value). (3) ORFS repaired hold at TT too (~-40 at TT, vclk fixed) -> opt-in FF-only hold repair (--hold-ff-margin). (4) old kits carried pre-0231295e92 tap_balance (spread > 80 on t1 t11 t23 t33). (5) arst_n -> rsync recovery (t28 -122, wire-RC dominated; t9/t25/t27 loops) watched after SLEW_MARGIN.
- branch claude/elem-s81-st405-1024: 6c9780bdff (generator fix), 95e3a5b3c3 (schema.py), b45417e66d (pre-route review PASS-COND results/geom_review/elem_s81_station405B_review_1024.json). NOT merged (lane reviews).
- launched 36 cold runs (ot-run 36 GB/8 thr): B (plan share 0.16, FF-only hold margin 5) x32 epyc3/localhost/intel1/intel2; A (0.08, FF-only margin 0) t12 t2 t15 t33. Kits localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kits{A,B} (epyc3 same; intel1/2 under scratch2). Logs .../elem-s81-st405/logs/t<N>.<V>.otrun.log, launches.txt. Also STA-only 0.16 re-signoff of the 17 c1 routes (sender reg2out at 0.84 T) running: epyc2/intel1 scratch2 elem-s81-st405/share016_sta.
- INCIDENT: my git stash crossed with ~/wt/hbm-arch (shared refs/stash); their changes saved as .../elem-s81-st405/FOREIGN_stash_popped_into_st405.patch (relayed by COORD). No more stash.
- 14:3x merged main 460bcf40fd (st405 @f25acc2468): opt-in --slew-margin/--cap-margin + --hold-ff-margin. The 32 B station kits regenerate
  byte-identical from canonical main, so they count. 0.16 re-STA of 17 c1 routes: sender reg2out min +179.3 (t24). Remaining: arst_n->rsync
  recovery t13 -20 / t28 -122 / t33 -14, t11 unpadded clk_t1 tap. A (0.08) runs = diagnostics.
- 14:49 st405 VERDICTS (B = plan share 0.16 + FF-only hold + SLEW/CAP margin + kit IR skip; DIE-STA seam STA on real views PENDING for all):
  SIGNED B t12 (TT +18.24 / FF +8.62, spread 45.3/41.1, DRV 0, DRC 0), B t15 (+13.40/+7.74, 73.5/58.7), B t17 (+10.29/+10.38, 36.4/33.4), B t21 (+9.82/+10.14, 65.2/50.4); records localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__t<N>/signoff/signoff.json.
  NOT SIGNED B t13: TT -67.37 = arst_n -> u_rsync_t12 recovery (capture clk_t12 sink at 161 ps: intra-tap skew 86 ps at CTS, routed ~25 ps below CTS estimate) + ft1_s0 eq in2reg -8.91 (same early leaf); FF +10.22, DRV 0. Diagnosis in progress (leaf-level clock pad toward plan insertion).
  A t15 (0.08 contract) diagnostic: NOT SIGNED TT -20.90 / FF -2.90 (DRV now 0): confirms the 0.08 window failure. A t12 STOPPED (B SIGNED).
  Station kits need > 36 GB in ORFS 6_report with per-kit PSM IR (peak 67 GB): kits now carry --skip-kit-ir (IR NOT RUN, TRIAL IR required); 6_report OOMs resumed warm from each kit's own 5_route.odb (resume_finish.sh, 64 GB; no P&R change).
  0.16 STA re-signoff of the 17 old c1 routes: sender ft reg2out at 0.84 T >= +179.3 ps (t24) on all 17 -> PASS (records epyc2/intel1:/srv/opentallas-scratch2/claude/elem-s81-st405/share016_sta/<type>/signoff_share016/).
  c1 (old recipe, superseded) finished since: t5 t8 t10 t14 t18 all NOT SIGNED (TT -36..-91, FF -18..-45).
  branch: main 460bcf40fd merged the st405 fixes; +4c37e60fb1 (--skip-kit-ir) on claude/elem-s81-st405-1024, not merged.
- 18:5x RESUMED after the 2nd limit (14:4x-17:00). Station B: t12 SIGNED (A t12 stopped); A t15 confirms the 0.08 failure (TT -20.9/FF -2.9).
  OWNER DECISIONS 18:4x adopted: pipelined synchronous reset from one root synchroniser (reuse KV-G3 kit_rsync; no recovery
  waivers), margins INFO only. Station + canonical-core sub-agents resumed with these.
- 2026-10-24 18:50 PDT: r1 (12:35) superseded: all 23 face_guard FAIL from RTL boundary (shared/self-loop output flops, unused inputs, 1-station pairs, [0:0] buses lost by slang). Fixes on branch d1852f8f10 (no RTL change): POST_SYNTH pin_reg_split output clones + unused-input capture flops + 1_synth.v, default Yosys frontend, explicit `pair IN OUT` one-station core pairs in face_guard (+test). Local synth checks: rstg/LLd/cfg7_bfp face_guard PASS. r2 stage-1 (place) running on all 29 (+ head spo kit via LEF contract). Reset: kit SDC times rst as a synchronous input (input delay max 0.5T / min -40 vs vclk; recovery/removal checked), no false path -- same as VQ r12. Blocked: xfin (main RTL has ENG ports, 102 bits not in plan pins), cfifo_crs4 (6-clock CDC landing, needs a multi-clock contract), capc5r/bksel_q (unsigned hard children), spr (ot_s81hd_key.sv not on main).
- 19:0x epyc2 scratch2 prune (COORD urgent): freed ~204 GB (19 -> 223 GB free); see HANDOFF.
- 19:1x st405 B VERDICTS (B = share 0.16 + FF-only hold + SLEW 50/CAP 20 + --skip-kit-ir; IR NOT RUN in every record (TRIAL IR required); DIE-STA seam STA on real views PENDING for all):
  SIGNED B t16 (TT +13.02 / FF +10.23, spread 37.9/33.3, DRV 0, DRC 0) localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__t16/signoff/signoff.json
  SIGNED B t20 (TT +12.05 / FF +9.97, spread 40.6/33.8, DRV 0, DRC 0) localhost:.../kitsB/slice_station__t20/signoff/signoff.json
  (earlier SIGNED: t12 localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__t12/signoff/signoff.json, t15, t17, t21 -> 6 SIGNED.)
  NOT SIGNED B t30: TT -81.43 = arst_n -> u_rsync_t13 recovery (2 endpoints, same class as t13); FF +9.86, DRV 0, spread 41.9. intel1:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsB/slice_station__t30/signoff/signoff.json
  NOT SIGNED B t11: DRV 4 slew (worst 371.9/320 on u_ft_ft0_s0 BUFx3 place-buffer -> INVx1 net, 149 um run); TT +12.94 / FF +9.90, spread 64.3/53.5 (current tap_balance: PASS). epyc3:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__t11/signoff/signoff.json
  NOT SIGNED B t34: DRV 2 slew (330/320, u_ft_ft2_s0, same net class) + TT pin-flop spread 88.6 > 80; TT +2.55 / FF +10.22. intel1:.../kitsB/slice_station__t34/signoff/signoff.json
  NOT SIGNED B t13: TT -67.37 recovery (unchanged).  A t2: TT -77.96 / FF -16.33 / spread 98.4; A t33: TT -27.67 / FF -43.8 / spread 116.6 (0.08 diagnostics, superseded by B).
  Recovery class (t13, t30) -> owner RESET RULE; requested the shared implementation in KV-G3.md (kit_rsync on main is still per-tap async; station kits get it from gen_rtl.py). No re-kit until it lands.
  Residual DRV class (t11, t34): repair_design at GRT (slew margin 50) leaves 1-4 near-miss nets with ~150 um place-buffer->INV runs; candidate = shorter max wire / post-route repair, not launched (needs review).
  B still routing (cold, 36 GB/8 t): epyc3 t1(6_report) t2 t23 t24 t33 (detail route) t3 t4 t9 t25 t27 t28 t32 (GRT); intel1 t31(6_report) t5 t10 t6 t8; intel2 t14 t18 t22 t26 t29. t4/t32 at GRT on epyc3.
  --skip-kit-ir: branch claude/elem-s81-st405-1024 e61ddd9234 (= 4c37e60fb1 + main merge), default unchanged (diff = 3 config lines only with the flag), die_plan tests 73 pass / 1 pre-existing fail. READY FOR MERGE.
## PARKED 18:56 PDT (station405 sub-agent)
- Branch: claude/elem-s81-st405-1024 @ e61ddd9234 (pushed; merged to main by COORD). No WIP and no stash. Worktree /srv/opentallas-scratch/claude/wt/elem-s81-st405.
- Watcher auto_resume.sh (localhost pid 745780) STOPPED by me at park, so it can't launch anything new. No new jobs were started.
- LIVE B jobs: ot-run launcher pid on localhost, container dpkit-slice_station__tN on the host; cold kits; 36 GB / 8 threads. Collect each with:
  grep ^SIGNOFF logs/tN.B.otrun.log
  - epyc3:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t1 (6_report, pid 2355875)
    - detailed route: t2 (2354717), t23 (2357829), t24 (2359058), t33 (2358944)
    - global route: t3 (2359361), t4 (2352217), t9 (2360299), t25 (2361702), t27 (2362857), t28 (2359247), t32 (2353081)
  - intel1:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t31 (6_report, 2386183)
    - t5 (2388643), t6 (2389368), t8 (2390102), t10 (2390720)
  - intel2:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t14 (2391131), t18 (2391528), t22 (2391812), t26 (2392084), t29 (2392476)
  - Logs: localhost:/srv/opentallas-scratch/claude/elem-s81-st405/logs/
  - If 6_report dies with Error 247, resume warm from the kit's own 5_route.odb with resume_finish.sh (manual now that the watcher is stopped).
- VERDICTS (B; IR NOT RUN; DIE-STA seam STA pending):
  - SIGNED: t12, t15, t16, t17, t20, t21. Records: localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__tN/signoff/signoff.json. Numbers in the 14:49 and 19:1x lines above.
  - NOT SIGNED:
    - t13: TT -67.37, recovery. localhost:.../kitsB/slice_station__t13/signoff/signoff.json
    - t30: TT -81.43, arst_n -> u_rsync_t13 recovery. intel1:.../kitsB/slice_station__t30/signoff/signoff.json
    - t11: DRV 4 slew, worst 372/320. epyc3:.../kitsB/slice_station__t11/signoff/signoff.json
    - t34: DRV 2 slew (330/320) and TT spread 88.6. intel1:.../kitsB/slice_station__t34/signoff/signoff.json
  - A (0.08 T) runs are diagnostic only: t2, t15 and t33 NOT SIGNED. t19 is the empty type and was NOT RUN. t7 belongs to Root.
- CAUSES:
  - t13/t30: the per-tap async reset synchronisers set up a recovery check across about 2 mm. The owner RESET RULE removes it.
  - t11/t34 slew: after the routing-stage repair at slew margin 50, a BUFx3 placement buffer still drives an INVx1 about 149 um away on the station-0 flop output, and it lands just over the limit.
  - t34 spread: tap balancing is done on the CTS-stage estimate; routed insertion comes out 20-30 ps low, and big taps have large internal skew.
- NEXT:
  1. Collect the 21 running tiles; write verdict lines here.
  2. t11/t34: write a slew-repair hook. ORFS repair_design_helper (util.tcl) passes only CAP/SLEW_MARGIN, with no max wire length. Use a kit tcl that runs repair_design -max_wire_length about 100 um, or a repair after routing on 5_2_route.odb followed by incremental detailed route. Review it, then re-run warm from each tile's own pre-fill route checkpoint.
  3. t34 spread: look at tap_balance on the worst tap.
  4. t13/t30: wait for the shared reset implementation (request with the 5 points is in KV-G3.md at 19:1x), then re-kit from main. If there is no ETA within about 2 h, offer to write the gen_rtl + kit_rsync implementation on a branch for KV-G3 to review.
- OWNER?:
  - Reset rule for a tile that is not its region's root: is rst_n a synchronous input with an input-delay budget, or is there one root synchroniser per tile?
  - Boot-cycle cost of the relay depth.

## PARKED 2026-10-24 18:56 PDT (canonical cores sub-agent)
- Branch claude/elem-s81-cores-1024 @dc52d4a06f (pushed; NOT merged). WT localhost:/srv/opentallas-scratch/claude/wt/elem-s81-cores. Commits: c111758856 generator+recipes, d1852f8f10 implemented-netlist face regs + face_guard `pair IN OUT` (+test), dc52d4a06f const-output flops / pair outputs / core_margin / LEF-contract mode.
- Generator: physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py (+recipes.json, core_face_post_synth.tcl, render_kit.py). VQ r12 recipe (833 ps, vclk 250, 60/25 split, seam hold -40, MCMM tc+bc, post-GRT DRV pass) on plan hard-core pins. rst is a TIMED synchronous input (max 0.5T / min -40 vs vclk, recovery/removal checked), no false path = owner reset rule, same as VQ r12. No RTL edits anywhere.
- Run root <host>:/srv/opentallas-scratch/claude/elem-s81-cores/<round>/<kit> (intel2 symlinked to scratch2); logs + bin/{launch,status,render}.sh on localhost. Only stage 1 (synth+face_guard+place) has run. NO route, NO signoff yet -> 0 SIGNED.
- LIVE (ot-run stage-1 place, all mine, leave running): localhost r2 l0r, l4, l4r, l5f, eg; r5 l1, l3, xrt1, xrt3 (const-flop fix); intel2 r2 l1c, l5_n32 (48 GB); intel1 r2 xfin (will FAIL face_guard: see below). Containers named klegacy-<kit>-<pid>.
- Stage-1 PASS (placed, placed.csv present, ready for review render + route): localhost r2 l0, l2, bk_g, LLd, cfg7_seq_bfp(intel2), r4 qbank_N, qbank_S, rstg, cfg7_seq, sstn_payload536. Reviews done: r2 rstg/cfg7_seq/payload536 (review/*.png): rstg PASS-COND; cfg7_seq REVISED (4.32 margin left an 8.6-um core, bins >0.8 -> core_margin 1.08 in r4); payload536 REVISED (face_flops cloned every 1-station flop -> pair outputs skipped in r4). r4 renders not yet viewed. No geom_review record committed yet.
- FAIL causes: r2 bksel_c face_guard shared 146 (r2 hook predates const-output fix; regenerate like l3 and rerun); nodes LLfd/LLfu/NNfd/NNfu + sstn_base566: RTL ORs a fault/status INPUT (fi / e0,e1,c0,c1,si,nf) into the fault flop -> face_guard 'unregistered' (OWNER?); xfin: main RTL has ENG ports (mode, e_v/e_c/e_hh/kk/dd, ~100 bits) absent from plan pins (OWNER?/S81 plan); cfifo_crs4: 6 clocks (cr, cr_s, xk[3:0]) CDC landing, single-clock SDC invalid (needs multi-clock contract); capc5r, bksel_q: unsigned hard children (generator refuses); spr: ot_s81hd_key.sv not on main (only 3ff002b64c); gunit signoff of legacy runs: 0/9 (sibling, "## gunit signoff").
- NEXT: (1) wait for live stage-1; bin/render.sh <rnd> <kit> <host>, Read PNG, write results/geom_review/elem_s81_core_<kit>.json; (2) route on the SAME host: bin/launch.sh <rnd> <kit> route 32 16 <host> (run_kit.sh continues from place, then do-finish/abstract, pin audit, signoff.py tt,ff -> <kit>/signoff/signoff.json); (3) regen bksel_c (r6) and rerun stage 1; (4) on SIGNED copy LEF/libs/signoff.json into physical/die_plan/s81/cores/views/<module>; (5) l5_n32 uses plan l5 outline 345.6 (n32 kit was 388.8): watch utilization; (6) refresh kit files of r2 survivors from current generator (only core_face_post_synth.tcl/freeze differ; no-op without TIE outputs).
- OWNER?: (a) fault/status inputs ORed combinationally into the fault flop (5 network nodes, sstn_base566): conforming to register-on-every-pin needs +1 cycle on the fault/status chain + bench update; (b) xfin plan pins vs main ENG-mode RTL; (c) cfifo_crs4 multi-clock boundary contract; (d) capc5r/bksel_q: sign children first or flatten; (e) implemented-netlist face registers (output clones / unused-input capture / constant-output flops, all 0-cycle, no RTL) accepted as the face_guard remedy?

## PARKED 2026-10-24 18:56 PDT (ELEM-S81 lane, root agent)
- Branches:
  - claude/elem-s81-1024 @18c5f769c2, merged in main e7c09034ae.
  - claude/elem-s81-st405-1024 @e61ddd9234, merged in main bf6ac37681 (with 460bcf40fd).
  - claude/elem-s81-cores-1024 @dc52d4a06f, NOT merged. Ungated: it changes the shared face_guard.py (pair IN OUT), so it needs review + signoff evidence first.
  - wt-bind48 (localhost elem-s81/wt-bind48, uncommitted v4.8 bind scripts): dead sub-agent, superseded by S81 p11.
  - No stash anywhere.
- Live jobs: none of my own. The sub-agent jobs are listed in the two PARKED blocks above: 21 station B routes on epyc3/intel1/intel2, and stage-1 core places on localhost/intel1/intel2. All watchers are stopped.
- Adopted Codex jobs, now finished:
  - BK drain full-layer replay (epyc3:/srv/opentallas-scratch/claude/codex-s81/bk_drain_layer, own sink-ON kit): build rc 0, run rc 0,
    TB_DV_SLICE FAIL, 2 SCHEDULE_MISMATCH (cycle 6535 port 2244, cycle 6546 port 2248: got 0, want data), fault_cycles 0, 6652 cycles.
    So the addressed-drain candidate is NOT adoptable as is. Default OFF on main stays correct.
  - Head abstract PSM c2 (intel2 scratch2 codex-s81/trial_head_psm_c2): PDN/bumps connected PASS, then the IR analysis crashed with
    OpenROAD signal 11 after 2:30 h (119 GB RSS). IR NOT RUN (crash). It needs TRIAL IR with a coarser grid or a newer OpenROAD.
- Results:
  - station405 B: 6 SIGNED (t12 t15 t16 t17 t20 t21; IR NOT RUN, DIE-STA seam pending).
  - NOT SIGNED: t11 and t34 (slew; t34 spread 88.6), t13 and t30 (reset recovery -> owner reset rule).
  - Legacy gunit routes through signoff.py: 0/9 SIGNED. The old recipe is superseded by the canonical rekit.
  - Canonical cores: stage 1 only, 0 SIGNED.
  - Disk: freed ~349 GB on localhost and ~204 GB on epyc2 scratch2; removed 104 GB from the epyc2 root disk.
- Failures pending owner decisions: see the OWNER? items in the two sub-agent PARKED blocks above.
- Next, in order:
  1. Collect the 21 B tiles. Resume any 6_report that hit exit 247 by hand with resume_finish.sh.
  2. Write the t11/t34 slew hook.
  3. Re-kit t13/t30 under the reset rule, using the shared KV-G3 implementation.
  4. Run review/route/signoff for the canonical cores, starting with the stage-1 PASS kits.
  5. Old frame kits: S81 owns them.
  6. Not run: dsdv_eng_tap(_w), idx_tx_n32, bf_front_roots, bf_col and elem_q have no kit in the repo; head hd_spn/serdes/lep0N/mesh/ctl/host are blocked on plan sources.
- OWNER?:
  - The reset delivery contract for non-root tiles and cores, and the boot-cycle cost.
  - Network nodes and sstn_base566 OR fault inputs combinationally into the fault flop. Registering them costs +1 cycle.
  - xfin: the plan pins don't match main's ENG-mode RTL.
  - cfifo_crs4: the multi-clock boundary contract is undefined.
  - capc5r and bksel_q: sign their children first, or flatten them.

## CODEX notes 2026-10-24 21:10 PDT
CODEX took over: station result collection, pipelined-reset successors and residual DRV fixes on codex/elem-s81-st405-1024 (hub epyc1 scratch2/wt/codex-st405); canonical legacy cores assigned to CODEX legacy sublane.
Collected B results unchanged from latest branch 2cb4732766: 7 SIGNED (t5 t12 t15 t16 t17 t20 t21), 11 NOT SIGNED (t1 t2 t11 t13 t23 t24 t26 t30 t31 t33 t34), 14 active runs (t3 t4 t6 t8 t9 t10 t14 t18 t22 t25 t27 t28 t29 t32). Active runs left progressing. Existing max-wire successor t11 Bmw on epyc2:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsBmw/slice_station__t11 is alive in FF hold repair; no duplicate launched. Main already contains --max-wire-um. Reset t13/t30 successors being prepared with unified reset; route waits on revised clock review per owner decision 5. IR remains NOT RUN; seam STA pending.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over: current C3/station harvest and FTHOLD proof on codex/s81-fthold-1025 (isolated sparse tree localhost:/srv/opentallas-scratch/claude/wt/codex-s81-fthold). hcpost C3 m5/m0 NOT SIGNED: TT +80.81 ps, FF -2.31 ps / 2 endpoints; face_guard, DRC, DRV PASS. VQ f0 NOT SIGNED (-4.41 ps /60 FF endpoints +1 TT slew), f5b live epyc3. FTHOLD original t8/t37 proofs live intel2. Diagnosed t37 pre-placement setup-repair loop (6,873 endpoints -150.353 ps, >900 iterations zero changes): ideal capture clock and preserved hold cells, not propagated hold failure. Own t8 CTS successor uses REMOVE_ABC_BUFFERS=1 to bypass unplaced repair, holds remain dont_touch; images t8/t37 reviewed PASS-COND, record results/geom_review/codex_s81_fthold_1025.json. ot-run client log /srv/opentallas-scratch/claude/codex-s81-fthold/t8.cts.log. Original jobs untouched.

## CODEX notes 2026-10-25 02:42 PDT
Split ve_m/ve_s/vn_a/vn_b contact sheet viewed; GEOM PASS-COND records codex/geom-proto-1025@932357e56. Launched all 4 cores x m0/m5 in isolated CTS checkpoint copies /srv/opentallas-scratch2/claude/codex-s81-split, via ot-run from epyc1 (ve variants epyc1; vn variants spilled epyc2). FF-corner GRT repair before TT route/finish, no constraints/RTL/pins/cycles changed. Per-kit root *.otrun.log; run_route.log; final signoff/signoff.json. hcpost -2.31ps/2 output-endpoint failure has own FF-repair copies epyc2:/srv/opentallas-scratch2/claude/codex-s81-hcpost/hcpost_ff_m0,m5 (ot-run logs epyc1 same root/m0.otrun.log,m5.otrun.log). Original failures preserved signoff_parent_failure. Missing cores and PORTFIX gunit/bk_sel core_faces now delegated CODEX missing-cores sublane; source gaps being repaired.

## CODEX notes 2026-10-25 02:58 PDT — legacy rstg/payload closure
CODEX took over canonical legacy rstg/payload536 on codex/s81-legacy-1025, own WT /srv/opentallas-scratch/claude/wt/codex-s81-legacy. Viewed rstg_review.png + payload_review.png: aligned N/S buses, macro-free, short wires, sensible core margin; pin density below capacity; PASS-COND with actual CTS/routed RC pending. Copied placed r4 kits into epyc1:/srv/opentallas-scratch2/claude/codex-s81-legacy/kits/{rstg_m0,rstg_m5,payload_m0,payload_m5}, originals untouched. Updated current signoff/pair-skew,250ps±40ps clock-balance hooks, FF postCTS STOP gate and0/5ps hold variants; sameRTL/pins/SDC833/60/25. Four ot-run staged route/finish clients3602280..3602283; logs /srv/opentallas-scratch/claude/codex-s81-legacy/logs/*.log. Next harvestactual signoff and diagnoseeveryfailure.

2026-10-25 03:01 PDT CODEX legacy: initial4variants FAIL CTS RSZ0060 (528rstg/2417payload hold buffers). Cause1: clock tap regex excludes ck[0], so zero trees balanced. r2fix recognises trees (payload88->254ps,7delaycells) but FAILS same cap because cts_post runs unrestricted hold repair before the postCTSSTOPgate. r3successor copies use clockbalance only atCTS, then actualFFgate, then0/5ps GRT hold repair; launchedclients3613380..83, sameownkits parent.../{rstg_r3_m0,rstg_r3_m5,payload_r3_m0,payload_r3_m5}. Earlierfailures retained; noRTL/SDCchange.

2026-10-25 03:07 PDT CODEX legacy: r4route/finish collectedall4, NOTSIGNED. rstg TT/FF:m0+355.08/-9.48(60ep),m5+355.24/-5.99(32ep); payloadm0+339.33/-20.09(536ep),m5+344.18/-10.47(511ep); allDRC0,sdc_lint/face_guardPASS. Bothsingle-stagecores have no internalrelatedflop->floppaths, so pairgatefails nofinitepairs despite1psrstg/9.6pspayloadspread; escalatedtoCLOCKviaCOORD, nofalse0claim. Residualholds beingrepairedwithactual6finalSPEF andincrementalDRT inowncopy epyc1codex-s81-legacy/eco/{rstg_h0,rstg_h5,payload_h0,payload_h5}; clients3644314..17, holdmargins0/5, noRTL/SDC/clockchange. DefaultGRTrepairfailurefixedbySKIP_INCREMENTAL_REPAIR=1+explicitFFhold-onlyposthook; priorfailuresretained.

## CODEX notes 2026-10-25 03:09 PDT — missing cores / head frames
CODEX took over missing-core/head-frame tasks on codex/s81-missing-1025. 6502d0a04 supplies dataflow-oriented gunit/bk_sel placements using original core views; targeted G0C 29 structural face errors ->0 and off-track pins0. Full plan/station regen + pricing remains parent-owned before route.
Normal hd_spn source bindings fixed and actual planned relays realized in reusable tools/s81_head/spine_kit.py (8a2a5db7a): production565-bit lockstep PASS3000cycles; BW-depth7->6 mutant CAUGHT68 mismatches. Planned relay ages xw3/xe3/bw7/be5/xo6/bi6. Own place-only kit epyc1:/srv/opentallas-scratch2/claude/codex-s81-missing/spine_physical/hd_spn via ot-run; review spine_phys_review.png looked and PASS-COND, cap1500 sinks/tap. No physical closure claimed.
Eight pure FT head types x2 recipes attempted at .../head_ft: 8 own jobs exact-stopped for non-gating FF setup/repair loop + duplicate-HM launcher defect; 3 launcherFAIL2 (make target5); 5 NOT RUN (SSH255/probe list-index failure). Original files/logs preserved; no inherited jobs stopped. Own corrected warm hd_st_m_ffonly attempt2 now in DRT, FF hold-only repair then TT final signoff. Hold-repair failure class feeds FTHOLD parent, no clock relaxation.
Remaining actual gaps: hd_spn_end spo.o/spr.i bottom closure undefined; hd_mesh/ctl/host parent modules absent; hd_lep0N wrapper + binding absent; hd_serdes digital wrapper/source binding absent. Historical no-kit list partly obsolete: idx_tx_n32 has full ref_tile specs; BF roots/BF column/elem_q real source and views exist, but no current uniform SIGNED gate. Eng tap(_w) RTL + historical views exist but are not standalone hard cores in current plan. Current-plan gates, not old list, govern next re-kits.
2026-10-25 03:16 PDT INFRA -> ELEM-S81: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: /srv/opentallas-scratch/claude/elem-s81-st405 (109 GB, ot-run kitsB clients with spill copy-back). When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.

## CODEX notes 2026-10-25 03:25 PDT
- t12 wavefront m5/m0 NOT SIGNED: TT+18.81/+24.03ps, FF-11.95ps/2ep, pair TT43.99/FF38.66ps PASS, DRC0. Final guard falsely checked rst_o_0 as data (raw1374/1374 PASS): FIXED codex/s81-reset-signoff-1025@457ac639e, 34tests + actual t12 guard PASS1374/1374. Real residual reset output/internal relay hold has own extracted-SPEF ECO h0/h5 at codex-s81-station-eco; initial24GB attempt OOM25.15GB, resumed successful GRT at48GB via do-5_2_route. An ordinary-route driver mistakenly rebuilt frontend; only own exact containers stopped, diagnostics retained, direct-stage driver corrected.
- t30 m5/m0 NOT SIGNED: FF-8.01/245 and -11.46/281; TT related pair86.3/86.7ps (ft0_s2 bit541 clk_t9 ->s3 clk_t1), DRC3 on reset pins vsPG. CLOCK owns skew fix; RESET generic pin-PG fix codex/reset-pin-pg-1025@181eaa1e0 moves soft pins<=1.04um,0cycles, must regenerate/review before retry. Reset shared2 false guard failures fixed457ac.
- C3 RXSB NOT SIGNED solely FF-13.25ps/35ep. Own hcpost GRT-FF retries NOT SIGNED(-3.03/3,-3.57/1); true postRCX hold ECOs now codex-s81-core-eco/rxsb_route_h0,h5,hcpost_route_h0,h5 using do-route, hold-only0/5, latest signoff. Original failures untouched. Initial4 launches had missing external runner127, then wrong ordinary-route target; corrected self-contained copies and exact-stop records preserve those failures.
- Split VN_A m0/m5 GRT FAIL0183(net25861), after initial GRT0overflow inside native DRV insertion. New p0/p5 copies use placement RC for DRV, legalize before incremental route, skip native repair, FF hold-only0/5. Other split6 variants live; no SIGNED claim yet.
- FTHOLD t8 CTS structural PASS: FF-46.83/149ep (148FT input+1arst_n), TT input+54.5 across3732bits; t37 PASS FF-51.68/747ep. Old clock trees late(276..356ps), so CLOCK holds routes pending density fix. Actual discovered power failure14,928 disconnected PG terminals on7,464 dont_touch delay cells FIXED by explicit preGPL PG hookup; actual ODB now0missing. Source codex/s81-fthold-1025@9516fdda1 includes PG fix +181eaa +existing DEC12 two-beat contract;9Liberty tests+4096-cycle lockstep/mutantPASS,0cycles. New density-t8 proof39taps,max933sinks,max151.2um, image viewed, launching density_gen/slice_station__t8 (t8_density.cts.log).

2026-10-25 03:31 PDT CODEX CORRECTION legacy: historicalkit-localface_guardPASSusedrejectedpair-IN/OUTparser. CANONICAL face_guard FAIL merged132rstg/1072payload; notjustclockgate. Zero-internal-pairclockcensusnowPASS66/536allclocked. CLOCK/reset_targetsownsoff-defaultgenuine2stageRTL,+1cycleandphysicalgates. One-stageTT/FFpositiveevidenceretained; neverSIGNED/registered. results/s81_legacy_codex_1025/CANONICAL_FACE_GUARD_CORRECTION.json recordsfacts.

## CODEX notes 2026-10-25 03:35 PDT — HANDOFF
Parkednorm/frameFT/legacy/quantwork, fullhandoffCODEX-LOG.md. Latestquantprototypecodex/s81-quant-release-1025@35171f88a, correctedC8sharedLUTmax157/+154lastcapturecycles; finalnewtableproofQUALIFIEDexit0 epyc1codex-quant-release-c8-1025(unit3931212), logspreservednotyetcollectedtorepo. Actualfulltoken/P&Rstillowed. Legacyone-stagecanonicalfaceFAILmerged132/1072 despitepositiveTT/FF; CLOCKowns2stageOFF-defaultsuccessors. No livejobsornewOWNER? fromthissublane.

## CODEX notes 2026-10-25 03:36 PDT — parked for Claude reset
S81 missing-core/head non-tile branch codex/s81-missing-1025@4e4d8acad (LOCAL WIP; prior6502d0a04/8a2a5db7a/f5ccc9519/d0ffb0275 pushed). Core layout face/track gates0/0 but actual core-core relay RTL remains NOT IMPLEMENTED, explicitly held. Normal/endspine real relay exactness PASS3000 each, mutants caught68/40, both placements now COMPLETE (normal epyc3 unit2384296, end epyc1 unit3489931); view actual placed images before route. HeadFT corrected ffonly route final signoff pending epyc1:.../codex-s81-missing/head_ft/hd_st_m_ffonly (unit3050405). RealKP4 SerDes adapter good1200beat exact miter PASS; status mutant still live .../serdes_eq(unit3813238). Complete job paths/commands/failure diagnoses/OWNER items in CODEX-LOG handoff section. No main merge, no false closure, original jobs untouched.

## CODEX notes — Handoff to Claude 2026-10-25 03:36 PDT
S81 subgroup parked on RESET; all jobs preserved. Main summary in CODEX-LOG.md Handoff S81 subgroup. Exact FT source36915c557 pushed;178type cached outputG0C0E at epyc1 codex-s81-ft-exact/adopt178, not committed yet and predates nine fault feeders. New hcpost_h5 actualSIGNED TT+61.39/FF+3.68ps, views unintegrated. Core-pair relay metadata missing actualRTL remains held/assigned; one-stage legacy canonicalfaceFAIL remains, two-stage ruling20:42 ownedCLOCK. Child detailed handoffs follow; no newjobs/merges.

## CODEX notes — Handoff to Claude 2026-10-25 03:37 PDT
NEW hcpost SIGNED epyc2:codex-s81-core-eco/hcpost_route_h5/signoff_codex/signoff.json TT+61.39/FF+3.68,pair25.40/22.33,all gates PASS;h0alsoSIGNED.Views integration owed.457ac reset-output signofffix READY;7fd4237cb FTHOLD experimental pushed.Full exact live jobs/results/failures/OWNER in matching CODEX-LOG handoff.Active jobs preserved,no new jobs/merges afterreset.
2026-10-25 04:45 PDT GEOM-REVIEW-2 -> ELEM-S81/S81-PLAN: POST-ROUTE slice_station t27 (station405_c1 family): face IO basis + unbalanced station taps (E column FF ~165 vs ~220) + 912-um arst_n; wavefront kits must carry balanced station taps + per-corner IO basis (lanes/GEOM-REVIEW.md).
