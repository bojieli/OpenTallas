- 2026-11-18 05:14 PST SWEEP 487 unsigned rows (S81 333+19 no-row, QC 102+4, KV 50, HEAD 2 running); lanes/OWNERS-SWEEP.tsv, script bin/owners_sweep.py.
  UNOWNED 112: S81 83 (other flow error 19, kit_rtl 16, hold after CTS 15, global_place 9), QC 26 (24 cancelled superseded cbf_q*, 2 kit input missing cbx_q10), KV 3 (kv3_hub_Eo, kv3_io_cor_v1, kv3_pc).
  DEAD-OWNER 1: S81 dsdv_slice_c1x_C__t9.
  FAILED no relaunch >1h: S81 234, KV 4 (CLAND kv3_pv_v*), QC 2 (sle_hc0, sle_sc_v3).
  STALE >3h: S81 219, QC 48, KV 13; 19 S81 + 4 QC plan types have no kit-wave row (not enumerable).
- 2026-11-18 05:50 PST 05:50 sweep, 471 rows. S81: UNOWNED 37 (was 83), FAILED-no-relaunch 241 (234), STALE 220 (219), DEAD-OWNER 45 NEW (col_h10/h9 owners). QC: UNOWNED 13 (26), STALE 50 (48), FAILED-no-relaunch 5. KV: UNOWNED 3 (3), FAILED 0 (4), STALE 11 (13), DEAD-OWNER 7 NEW (kv3_hg_v1p6, kv3_hg_v3, kv3_hgi). KV-TYPES-SWEEP has no row and no agent id: not an owner. NOMCAP-1118 owns 73 rows but alive is blank (not in the id list).
- 2026-11-18 06:50 PST 06:50 sweep, 495 rows, 429 unflagged.
  S81: UNOWNED 2, STALE 5, FAILED 0, DEAD 0 (was 37/220/241/45); e.g. dsdv_slice_lepe_mu_LP__t2, seqhost__t1, s81sl_leaf__t65. col_h9_r2__t1 x2 only owner is Fable BANKLEAF (dead), co-owners S81-DIE-R3 alive.
  QC: UNOWNED 12, FAILED 1 (slw_hc0__cl1bc59e1c), STALE 48, DEAD-OWNER 2 (cbn_q01, cbn_q11 on FABLE-FIX-QC-N) (was 13/5/50).
  KV: UNOWNED 0, STALE 11, DEAD 0 (was 3/11/7); all cancelled-superseded 11 h, owners KV-D22-ROWS/KV-HG-OPUS alive.
  HEAD 0 flagged.
- 2026-11-18 07:50 PST S81 0/0/0/0; HEAD 0; QC UNOWNED 4 FAILED 2 STALE 10 DEAD 0; KV STALE 4 (kv3_hg_v1p6, kv3_hgi_v2 x2). QC unowned: slw_fe_v2__clf110fab2, slw_stm_v2__cl1ca9c415, slw_hc0__cl1bc59e1c. Failed-no-relaunch: slw_hc0, sle_ctl. 481/496 rows unflagged.
- 2026-11-18 08:50 PST S81 0/0/0/8 (U/F/S/D); QC 5/2/11/0; KV 0/0/4/1; HEAD 0
  vs 07:50: S81 +8 DEAD-OWNER (col_h10_r0_p4__t1, col_h9_r0_p1__t1 pv variants); QC U+1 F0 S+1
  KV +1 DEAD (kv3_pc__cl5a95b461); rows no flag 474/497
- 2026-11-18 09:50 PST 09:50 S81 5 unowned/46 failed-no-relaunch/11 stale (30+11+5 FAILED); QC 2/0/9/0; KV 0; HEAD 0
  S81 NEW: FAILED-NO-RELAUNCH 46 (s81sl_leaf__t44__clf4ea6d4b, s81sl_kv_leaf__t3, s81sl_kv_leaf__t4)
  S81 unowned: svc_hi_dsdv_svc_rs__t1, __t5, svc_lo_dsdv_svc_rs__t2
  no kit-wave row: S81 1, QC 14, KV 0, HEAD 0 (not reported)
  rows 493, no flag 436
- 2026-11-18 12:51 PST 12:5x sweep 494 rows; script fixed (newer LAUNCH/RELAUNCH-ON-FIX = relaunched). S81 UNOWNED0 FAILED10 STALE9 DEAD4; HEAD 0; KV 0. QC UNOWNED6 FAILED9 STALE16 DEAD8. DEAD owners QC-STRAGGLERS/S81-NORELAUNCH/FABLE-FIX-QC-STA last posted 09:52-10:22 (pre-limit). No-kit-wave-row: QC 14, S81 -1.
- 2026-11-18 13:50 PST 13:50 sweep 503 rows, 484 unflagged. S81 UNOWNED 0 / FAILED 10 / STALE 10 / DEAD 5. QC UNOWNED 0 / FAILED 4 (sle_su_l1, slw_su_l1; owned) / STALE 9 / DEAD 0. KV 0, HEAD 0. No-kit-wave-row: S81 -1, QC 4, KV 1. col_h9_r1 + QC cbx_q10 = HELD-INTENTIONAL (D8e, N4.1p).
- 2026-11-18 14:50 PST 14:50 sweep: S81 UNOWNED0/FAILED10/STALE10/DEAD5 (leaf t25,t54,t43; was 0/10/10/5). QC 0/0/9/0 (FAILED 4->0; STALE 9 sle_hc1, slw_stm_v1 x2). KV 0, HEAD 0. No NEW group. No-kit-wave-row: S81 -1, QC 4, KV/HEAD 0. 484 rows unflagged.
- 2026-11-18 15:51 PST S81 U0/F11/S11/D6 (was 0/10/10/5); QC U2/F0/S9/D6 (was 0/0/9/0); KV 0; HEAD 0. New: QC UNOWNED slw_hc2 x2, QC DEAD slw_stm_v1/v2. No-kit-wave-row: S81 -1, QC 4.
- 2026-11-18 17:50 PST 1750 U/F/S/D: S81 6/11/11/0, QC 2/5/9/0, KV 1/2/0/6, HEAD 0.
  S81 leaf rows (t25,t54,t43) still FAILED-NO-RELAUNCH+STALE; D8e relaunch not yet visible.
  QC FAILED: sle_su_l1 x2, slw_su_l1; STALE slw_stm/sle_hc1; UNOWNED sle_fe_v1, slw_fe_v2.
  NEW: KV 6 DEAD-OWNER, owner KV-D23-COMPOSE last post 14:48 (kv3_hub_C/Wo, kv3_pv_v1n/v2n/v3/v3n).
  Revived DEAD: none (0 DEAD on S81/QC).
- 2026-11-18 18:50 PST 18:50 vs 17:50 (U/F/S/D): S81 0/0/0/0 (was 6/11/11/0), QC 0/6/9/0 (was 2/5/9/0), KV 1/6+1/0/0 (was 1/2/0/6), HEAD 0. S81 leaf rows mapped to owners. QC STALE 9 are owned rows (FE/HC2/STM). QC su_l1 x4 FAILED-NO-RELAUNCH under PLAN-R3/FAIL-ROUTE-1115. KV hub/pv 7 FAILED-NO-RELAUNCH, kv3_hub_Wi has no owner row.
