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
- 2026-11-18 19:50 PST 1950 sweep: 507 unsigned rows (S81 352, QC 103, KV 50, HEAD 2) in lanes/OWNERS-SWEEP.tsv.
  UNOWNED 0, DEAD-OWNER 0, STALE>3h 0.
  FAILED-NO-RELAUNCH: KV kv3_pv, kv3_pv_v8 (other flow error, 2.4h, owner KV-D23-COMPOSE alive).
  505 rows unflagged; S81 D8e relaunches running; S81 plan 394 types, 43 signed.
  Action: KV-D23-COMPOSE to relaunch kv3_pv/kv3_pv_v8.
- 2026-11-18 20:50 PST 20:50 sweep: 507 rows, 502 unflagged, committed 3e52301.
  S81: UNOWNED gunit__t1 (place FLOW, 0.4h); UNCLASSIFIED s81sl_leaf__t56 (kit_rtl), svc_hi_dsdv_svc_pvso_entry__t1/t2 (place) - all owned by FAIL-ROUTE-1115, posted 20:38.
  KV: kv3_pv FAILED-NO-RELAUNCH+STALE 3.4h (route INFRA, owner KV-HUBPV-1118); kv3_pv_v8 now running/clean.
  HEAD, QC: no flags. Not verified whether kv3_pv has a live epyc7 job.
- 2026-11-18 22:52 PST 2250 sweep: 508 rows, 6 flagged, all S81; HEAD/QC/KV none.
  S81 UNOWNED 4: s81sl_leaf t40,t52,t53,t61 FAILED global_place 0.2-0.3 h; likely FABLE-FIX-S81-LEAF (name mismatch s81sl_leaf vs ot_s81sl_leaf, no agent_id) - confirm.
  S81 UNCLASSIFIED 2: svc_hi_dsdv_svc_pvso_entry t1 (S81-TAIL-1118) and t2 (FAIL-ROUTE-1115), owners alive, class other.
  No DEAD-OWNER, no STALE, no failed-no-relaunch flags.
  Rows: lanes/OWNERS-SWEEP.tsv
- 2026-11-18 23:51 PST 23:50 sweep: 508 unsigned rows S81/HEAD/QC/KV, 487 unflagged. HEAD, QC, KV: 0 flags. S81: 13 UNOWNED all s81sl_leaf__t* global_place FAILED (family covered by FABLE-FIX-S81-LEAF, so no new lane unless it lacks them). S81 FAILED-NO-RELAUNCH 11 (eng__t1, gunit__t1, leaf t40/t52/t53/t54/t61/t75...). S81 UNCLASSIFIED 2: dsdv_slice_c1x_C__t9, s81sl_leaf__t56. No DEAD-OWNER, no STALE.
- 2026-11-19 00:51 PST 508 unsigned rows (S81 352, QC 103, KV 51, HEAD 2); HBM skipped.
  UNOWNED 0, DEAD-OWNER 0, FAILED-NO-RELAUNCH-1H 0, UNCLASSIFIED 0.
  STALE>3H 2 (KV kv3_hgi_v3, kv3_pv), both family-covered (FABLE-FIX-KV-HG, KV-HUBPV-1118).
  Largest owners: KIT-WAVE(auto) 170, FABLE-FIX-S81-COLH9R1 83, WAVE-PILOT-FIX 74, FABLE-FIX-QC 30.
  Nothing needs a new lane.
- 2026-11-19 01:52 PST 0350 sweep: 507 rows (S81 352, QC 102, KV, HEAD), 504 unflagged, 3 flagged.
  UNOWNED 0, DEAD-OWNER 0, FAILED-NO-RELAUNCH-1H 0.
  STALE>3H 2: kv3_hgi_v3, kv3_pv (cancelled superseded 4.6h; family owners FABLE-FIX-KV-HG/PV covered).
  UNCLASSIFIED 1: s81sl_leaf__t56 (FAILED kit_rtl 0.9h; FABLE-FIX-S81-LEAF posted 01:29).
  Largest lanes: KIT-WAVE(auto) 164, FABLE-TYPE-REDUCE-S81-COL 117, S81-GEOM-OPUS ~64.
- 2026-11-19 02:50 PST 02:50 sweep: 508 rows, 45 flagged, 463 clean. S81: 11 UNOWNED + 5 FAILED-NO-RELAUNCH (leaf t3/7/13/14/32/33/40/54/66/73, col_h9_r0_p1) all in live family lanes (FABLE-FIX-S81-LEAF 02:35, S81-DIE-R3 02:40). 11 serdes CBC-FALLBACK covered by FABLE-FIX-S81-SERDES 02:48. KV: 4 qkd_kvs_pc* UNOWNED (cancelled-superseded, 28-357h) -> KV-D23-COMPOSE; 14 STALE cancelled-superseded kv3_* all owned. HEAD hd_mesh CBC-FALLBACK running, CBC-RULES live. No uncovered rows.
- 2026-11-19 03:52 PST 03:51 rows 508, 401 unflagged. S81: UNOWNED 44 (35 s81sl_leaf, 3 svc_lo_dsdv_svc_rs, 3 col_h9_r0_p1, 3 other); FAILED-NO-RELAUNCH 58 (13 also UNOWNED+STALE); STALE 39; CBC-FALLBACK 11; UNCLASSIFIED 4. KV: UNOWNED 4 (qkd_kvs_pc*, all STALE), STALE 17 (kv3_hgi_v2/v3). QC: none flagged. HEAD: hd_mesh CBC-FALLBACK only. DEAD-OWNER 0, BIND-STALE 0. File lanes/OWNERS-SWEEP.tsv
- 2026-11-19 04:51 PST 0450 sweep (38bb4eec): 508 rows, 111 flagged. S81 FAILED-NO-RELAUNCH 85 (was 58), STALE 58 (39), UNOWNED 4 svc cancelled-superseded (was 44), DEAD-OWNER 1 (svc_pvso_entry t1), UNCLASSIFIED 4, CBC-FALLBACK 11. KV STALE 13 (17), UNOWNED 0 (was 4). HEAD only hd_mesh CBC-FALLBACK. Unowned svc rows are SVC-REPLAN (H8 form), not failures. Main worry: FAILED/STALE growth on S81 col_h10_r0_p4 + s81sl_leaf.
- 2026-11-19 05:52 PST 11-19 05:5x sweep: 506 rows (S81 348, QC 101, KV 54, HEAD 2), 335 unflagged
  S81: 1 UNOWNED (svc_hi_dsdv_svc_pvso_entry__t2), 99 FAILED-NO-RELAUNCH, 142 STALE, 4 UNCLASSIFIED, 18 CBC-FALLBACK
  HEAD: hd_mesh CBC-FALLBACK only; QC: 0 flags
  KV: 15 stale rows tagged WAIT-BIND (no bind of record; owners FABLE-FIX-KV-HG / KV-D23-COMPOSE), 0 UNOWNED
  owners_sweep.py extended with KV WAIT-BIND; DEAD-OWNER 0; file lanes/OWNERS-SWEEP.tsv committed
- 2026-11-19 06:52 PST 06:52 sweep 509 rows (S81 351, QC 101, KV 55, HEAD 2); UNOWNED 0, DEAD-OWNER 0, FAILED-NO-RELAUNCH 0, STALE 0 (outside WAIT-BIND).
  WAIT-BIND rule had been lost from owners_sweep.py (TSV only had old tags); re-added: KV not-running UNOWNED/DEAD-OWNER/STALE -> WAIT-BIND, owner FABLE-FIX-KV-HG / KV-D23-COMPOSE. KV WAIT-BIND 17.
  S81: 301 KIT-WAVE LAUNCH + 58 RELAUNCH-ON-FIX since 06:40 (BOUND-FALLBACK 06:40:52 on D8f tree); 349 rows running; 11 CBC-FALLBACK families flagged.
  40 S81 hold-after-CTS rows owned by S81-CLOCK-WINDOW-1119 (running, no flag). HEAD 2 running (hd_mesh CBC-FALLBACK); QC 101 running.
  Committed lanes/OWNERS-SWEEP.tsv + bin/owners_sweep.py
- 2026-11-19 07:54 PST OWNERS-SWEEP-09xx 07:55: 470 unsigned rows (s81 351, qc 62, kv 55, head 2; cores 0 open except kv). Flagged: UNOWNED 105 (s81 71, qc 14, kv 10... see tsv), DEAD-OWNER 61 (mostly KIT-WAVE-1 STALE.tsv fallback), STALE s81 49 + head 1, STALE-KV-FALLBACK kv 55 (not owner faults).
  FAILED-NO-RELAUNCH 0: 152 s81 FLOW ssh TimeoutExpired rows are 0.8 h old, inside the 1 h grace; recheck next tick.
  Suggested owners: s81 unowned -> S81-FAILED-TRIAGE-1119 / FABLE-TYPE-REDUCE-S81-REST; qc unowned -> TYPES-QC-FAIL-1115; kv unowned -> KV-PC-HGI-1119 after WAVE-PILOT-FIX.
  File: lanes/OWNERS-SWEEP.tsv (owner = latest 6 h post/handoff naming the item or its family).
- 2026-11-19 07:54 PST OWNERS-SWEEP-09xx CORRECTION: exact counts UNOWNED 95 (s81 71, qc 14, kv 10), DEAD-OWNER 65 (s81 37, qc 23, kv 5), STALE s81 49, head 1; supersedes the totals in the previous post.
- 2026-11-19 08:52 PST 0945 sweep, 466 rows (S81 351, HEAD 2, QC 62, KV 51). Flagged 99 vs 470-row 07:56 sweep with 321 flagged: UNOWNED 0 (was 71 s81+14 qc+10 kv), DEAD-OWNER 0 (was 37+23+5) after S81-OWN-1119, QC-OWN-1119, KV-PC-HGI-1119 took the rows. FAILED-NO-RELAUNCH 0 and INFRA-COPY 0: all failures relaunched, S81 350 and QC 62 rows now running. STALE (running >3 h, no kit change): S81 38 (col_h9/h10, dsdv_slice_c1x_C, owner S81-OWN-1119), KV 41 (kv3_hg*, hgi*, pv*, pc*, up to 32 h), HEAD 1 (hd_mesh 9.2 h). STALE-EPYC7: KV kv3_hub_Ei, kv3_sys_c. KV WAIT-BIND 7 (cancelled, await D25 bind); S81 CBC-FALLBACK 11 (serdes). Table lanes/OWNERS-SWEEP.tsv
- 2026-11-19 11:46 PST 11:45 sweep, 477 rows (S81 351, QC 74, KV 51, HEAD 1). UNOWNED 0, FAILED-NO-RELAUNCH 0, INFRA-COPY 0, BIND-STALE 0; DEAD-OWNER 2 (S81 s81sl_leaf__t72 TL-LEAFT72, svc_hi_dsdv_svc_pvso_entry__t1 S81-CORES-2 +UNCLASSIFIED); LIMIT-PAUSE 5 (s81sl_leaf t8,t14,t28,t52,t67, S81-OWN-1119 last post inside 09:00-11:40 usage limit).
  STALE >3 h: S81 179 (was 38; the 07:39 relaunch wave has crossed 3 h, still RUNNING route), KV 43 (was 41), HEAD 0 (was 1, hd_mesh no longer listed). STALE-EPYC7: KV kv3_hub_Ei 1 (was 2). WAIT-BIND KV 7 unchanged; CBC-FALLBACK S81 serdes 11 unchanged.
  Suggested owners: leaf_t72 -> S81-OWN-1119; pvso_entry__t1 -> S81-CORES-2 relaunch; S81 stale col_h9/h10 -> S81-OWN-1119 + TYPE-S81-FLOWERR; KV stale kv3_hg*/pv*/pc* -> KV-SYSC-1119 / KV-PC-HGI-1119; serdes CBC -> CBC-RULES-1119.
  Table lanes/OWNERS-SWEEP.tsv committed.
- 2026-11-19 11:52 PST 11-19 12:0x sweep 477 rows. STALE split (was KV 43, S81 179): KV NOLOG 35 + NOKIT 8; S81 NOLOG 28 + NOKIT(rt_mirror_copy_epyc7, no log) 139, ROUTE-LONG 2, LOGFRESH 1. STALE-EPYC7 KV 32 (was 1), S81 4. DEAD-OWNER S81 2 (t72, pvso_entry), QC 1 (cbn_q11 cl49ae4555), LIMIT-PAUSE S81 5 unchanged. CBC-FALLBACK 11, WAIT-BIND KV 7, UNCLASSIFIED 1 unchanged. NOLOG jobs possible ghosts: kv3_hg family since 11-18 17:00.
- 2026-11-19 12:50 PST 12:50 sweep, 476 rows. S81: NOKIT 140 (was 139, none moved), STALE-NOLOG 24, ROUTE-LONG 5, UNOWNED/LIMIT-PAUSE 5, CBC-FALLBACK 11, DEAD-OWNER 2.
  KV: STALE-NOLOG 35->16, 19 now STALE-LOGFRESH (relaunched after KV-PC-HGI cancels), NOKIT 8, EPYC7 32, WAIT-BIND 7.
  QC: 1 DEAD-OWNER cbn_q11__cl49ae4555 (TYPES-QC-FAIL-1115).
  Infra-dead/rt-mirror re-pick has not yet moved the 139 rt_mirror_copy_epyc7 rows.
  Suggest S81-STALE-RELAUNCH for NOKIT; KV-PC-HGI-1119 for KV EPYC7.
- 2026-11-19 13:52 PST 14xx sweep: 478 unsigned rows (S81 349, QC 77, KV 51, HEAD 1), committed ef3281ea.
  UNOWNED 0; FAILED-NO-RELAUNCH 0 (7 S81 FAILED bind-stale rows relaunched <1 h).
  DEAD-OWNER 7 QC rows: FABLE-FIX-QC (4), SONNET-FIX-QC (3) last post 11:49, no successor named.
  STALE >3 h: KV 33 (worst kv3_io_cor 37.2 h), S81 23, QC 1; KV WAIT-BIND 6.
  FABLE-FIX-* renamed to OPUS-FIX-* (QC-COLLCORE, KV-HG, S81-LEAF, S81-LEPE, KV-PV) and counted live.
- 2026-11-19 17:50 PST 18xx sweep 17:49: 481 rows (S81/HEAD/QC/KV), 441 unflagged, 24 KV WAIT-BIND.
  UNOWNED 3 (QC slw_sc_v1 cl4590432d + cl5e017c6f; S81 dsdv_slice_lepw_mu_C__t1 lint fail at gen).
  DEAD-OWNER 0 (S81-OWN-1119 in agent_ids, resumed 17:50).
  FAILED-NO-RELAUNCH 15 (S81 10 mostly bind stale re-bind, QC 5); STALE 16, worst 4.7 h (S81 slice_station t36, svc_hi_pvso_entry t1).
  Detail lanes/OWNERS-SWEEP.tsv
- 2026-11-19 18:51 PST 499 unsigned rows (prev 481): +18 QC, 0 gone. Flags 18 -> 11 (FNR 14->7, STALE 15->7, UNOWNED 3->1, WAIT-BIND 24->2).
  New owners applied: COL-H10-1119 24 col_h10_r1/r2 rows, COL-CENSUS-1119 93 other S81 col rows (no posts yet, not DEAD-flagged); S81-GEOM-OPUS keeps D8i col types.
  UNOWNED: s81 dsdv_slice_lepw_mu_C__t1 (failed, stale). STALE s81: slice_station__t36, svc_hi_dsdv_svc_pvso_entry__t1 (S81-OWN-1119).
  FAILED-NO-RELAUNCH qwen_compute 6: cbn_q11__cl49ae4555, cbn_q11__cl5cc92dfe, slw_su_c__cl19bb38ef, slw_su_c__cl92142dac, slw_st_a_v2__cl9f076a5c, tt_ctlm.
  KV 2 WAIT-BIND (kv3_pc__cl5a95b461, qkd_pv_fin_s8_pin); s81_head clean.
- 2026-11-19 19:51 PST 19:50 sweep 6a62fd41387: 502 unsigned rows (s81 351, qc 98, kv 51, head 1); flags 16 vs 11 prior.
  Cleared since 18:51: cbn_q11 x2, tt_ctlm, slw_st_a_v2, slice_station__t36, svc_hi t1, dsdv_slice_lepw_mu_C__t1 (relaunched/running).
  Still flagged: slw_su_c cl19bb38ef + cl92142dac FAILED-NO-RELAUNCH+STALE (5-6h, SONNET-FIX-QC).
  New: 14 slw_su/st/stm rows DEAD-OWNER (QC-SUST-MACRO-1119 has no post yet).
  KV kv3_pc__cl5a95b461 and qkd_pv_fin_s8_pin wait on D25e bind (KV-D23-COMPOSE); +2 new rows phy__t1, seqhost__t1.
- 2026-11-19 20:51 PST STATE [OWNERS-SWEEP -> COORD] 519 unsigned rows (S81 351, HEAD 9, QC 108, KV 56) via bin/owners_sweep.py, lanes/OWNERS-SWEEP.tsv.
  UNOWNED 0, DEAD-OWNER 0, STALE 0 (KV kv3_pc__cl5a95b461 WAIT-BIND 7.7h, owner lane alive).
  FAILED-NO-RELAUNCH 1: KV kv3_hub_Wi (place fail 19:16, 1.6h; owner FAIL-ROUTE-1115 +KV-D23-COMPOSE).
  Failed under 1h, not flagged: QC 5 src_manifest (cbx_q10__cl94a12200, slw_su_c__cl19bb38ef, +3) UNCLASSIFIED; S81 slice_station__t51 place.
  CBC-FALLBACK info: S81 slice_station__t36/t43/t51/t52 (owners S81-OWN-1119, FABLE-FIX-QC).
- 2026-11-19 21:50 PST 21:50 sweep: 519 unsigned rows (S81 351, QC 108, KV 51, HEAD 9); 424 no flag.
  UNOWNED 2: S81 s81sl_leaf__t21 (place fail; leaf family now FABLE-FIX-S81-LEAF-2140), QC cbf_q00__cl870de686 (src_manifest).
  FAILED-NO-RELAUNCH 1: S81 slice_station__t51 (place, 1.3 h, owner FABLE-FIX-S81-LEAF alive).
  DEAD-OWNER 0, STALE 0; CBC-FALLBACK S81 79 (slice_station__t52, s81sl_leaf__t1); QC UNCLASSIFIED 16 (cbf_q00_s2).
  KV 51 rows all flagged-free; pv family owned by FABLE-FIX-KV-PV-2140.
- 2026-11-19 22:51 PST 22:50 sweep: 518 unsigned rows S81/HEAD/QC/KV (351/9/108/51), 19 excluded as NOT-IN-PLAN (sram/rom/d2d/phy: QC 10, HEAD 8, S81 1).
  UNOWNED 2 raw (s81sl_leaf__t42, t52) -> covered by FABLE-FIX-S81-LEAF-2140 family; FAILED-NO-RELAUNCH 2: s81sl_leaf__t21 (leaf-2140), slice_station__t51 (S81-DIE-R3); other FAILED: leaf t60, serdes__t16, KV kv3_hub_Wi, qkd_pv_fin_s8_pin.
  DEAD-OWNER 11 QC rows owned by QC-PADLEG-1119 (no post in 2 h): sle_sc_v2, sle_sc_v3, slw_sc_v2, sle_fw_v2__cl*.
  Running >3 h: 106 (S81 ~60, QC ~35, KV 4; KIT-WAVE auto 48), tool did not flag STALE; CBC-FALLBACK 79 S81.
  file lanes/OWNERS-SWEEP.tsv committed.
- 2026-11-19 23:51 PST 23:55 sweep: 500 plan rows (19 sram/rom/NOT-IN-PLAN excluded). UNOWNED 31 (S81 16 dsdv_*/svc_*, QC 13 hc*/cbf_q01/native59, KV 2 kv3_hub_E*). DEAD-OWNER 14 (KV-PC-PG-2330 no post today: 6 kv3_pc*; coll_ftc FABLE-FIX-QC; COL-H10-1119 2). FAILED-NO-RELAUNCH 5 (leaf t42/t52, slice_station__t51, serdes__t16, kv3_hub_Wi). STALE ~14 (leaf t38/t50/t57, QC slw_hc0/hc2, kv3_hroot). 36 QC src_manifest failures 23:02 hit 1h at 00:02.
- 2026-11-20 00:50 PST 00:50 sweep: 519 unsigned rows (S81 351, HEAD 9, QC 108, KV rest), HBM skipped.
  UNOWNED 3 S81: s81sl_leaf__t37, t47, t51 (all FAIL place FLOW, other flow error).
  DEAD-OWNER 0. STALE: slice_station__t51 (4.3 h, owner CBC-RULES-1119 posted 00:17).
  FAILED-NO-RELAUNCH >1h: S81 leaf t42, t52 (FABLE-FIX-S81-LEAF-2140), serdes__t16, slice_station__t51, t37, t51; KV kv3_hub_Wi (KV-D23-COMPOSE).
  CBC-FALLBACK 79 S81 rows; file lanes/OWNERS-SWEEP.tsv
- 2026-11-20 01:50 PST 01:50 sweep: 519 rows (S81 351, QC 108, KV ~51, HEAD 9). UNOWNED 0, DEAD-OWNER 0. FAILED-NO-RELAUNCH 8 (S81 7: leaf t37/t42/t47/t51/t52, serdes t16, slice_station t51; KV kv3_hub_Wi). STALE failed/signed 5 (S81 t42,t52,serdes t16,slice_station t51; QC sle_su_l1 clc6d66f5b signed-pending 9.4h). RUNNING >3h: ~190 rows, oldest KV kv3_io_cor 49h, S81 dsdv_slice_iq/kv512/c1x_C 19-40h, QC sle_* 10-16h; see lanes/OWNERS-SWEEP.tsv
- 2026-11-20 02:50 PST hourly sweep: 518 rows (S81 351 QC 107 KV/HEAD rest). UNOWNED 0, DEAD-OWNER 0, STALE 0. FAILED-NO-RELAUNCH 1 (KV kv3_hub_Wi, WAIT-BIND). UNCLASSIFIED 2 (S81 col_h10_r1__t1__cld01bb4ae, col_h10_r2__t1__clac068e56). 11 CANCEL-UNSIGNABLE jobs treated as cancelled. RUNNING >12h listed in lanes/OWNERS-SWEEP.tsv
- 2026-11-20 09:50 PST 09:50 sweep lanes/OWNERS-SWEEP.tsv: 498 rows (S81 351, QC 95, KV 51, HEAD 1); 493 unflagged, 5 flagged.
  KV: kv3_hub_Wi FAILED other flow error 3.4h and kv3_pv_v8 bind stale vs plan 3.7h, both FAILED-NO-RELAUNCH, owner KV-PLAN-R1 alive (posted 09:35).
  S81: col_h9_r0_p1__t1__pva2e3974f FAILED src_manifest UNCLASSIFIED 6.5h (owner FAIL-ROUTE-1115, posted 09:28, no relaunch); col_h9_r0_p3__t1__cl31d0dc4b cancelled-superseded STALE 6.0h (PROGRESS-WATCH alert only).
  S81 col_h9_r0_p6__t1__pv0012ba28 cancelled-superseded 2h UNOWNED. HEAD hd_lep0N running 13h, owned (GRT-TRIAGE/HEAD-R14). QC: none flagged; no reset-identity rows flagged.
- 2026-11-20 10:50 PST 10:50 sweep: 8 flagged of ~500 rows, owners incl QC-PLAN-R5, FLEET-WATCH-1015, FABLE-PD-S81-1100.
  KV: kv3_hub_Wi other flow error 4.4h, kv3_pv_v8 bind stale 4.7h: FAILED-NO-RELAUNCH, owners alive (KV-PLAN-R1, PROGRESS-WATCH).
  S81: col_h9_r0_p1__t1__pva2e3974f src_manifest UNCLASSIFIED 7.5h, no relaunch, owner S81-DIE-R4 alive.
  S81: dsdv_slice_kv512_C__t1 placed/route held, DEAD-OWNER OPUS-FIX-S81-SLICEC no post 2h.
  QC: 3 UNCLASSIFIED other flow errors (sle_ctl padE0, sle_stm_v1, slw_hc2), owner FAIL-ROUTE-1115 alive; HEAD none.
- 2026-11-20 11:50 PST 11:50 sweep: 496 rows, 13 flagged.
  KV: kv3_hub_Wi 5.4h, kv3_pv_v8 5.7h, kv3_pc_v1__cl23f6a148 FAILED-NO-RELAUNCH (owners alive); kv3_hgi_v1, kv3_hub_Ei, qkd_pv_fin_s8_pin on dead FABLE-FIX-KV-HG/KV-D23-COMPOSE (WAIT-BIND).
  QC: slw_hc2 (UNCLASSIFIED) and slw_st_a_v2 (global_place) FAILED-NO-RELAUNCH, owner FAIL-ROUTE-1115 alive.
  S81: col_h9_r0_p1__t1__pva2e3974f 8.5h STALE/UNCLASSIFIED; dsdv_slice_kv512_C__t1 DEAD-OWNER; s81sl_leaf__t21, t26, svc_lo_dsdv_svc_rs__t6 UNOWNED.
  HEAD: none flagged.
- 2026-11-20 12:50 PST 12:50 sweep: 31 flagged rows, 24 new since 11:50.
  S81 new: 15 UNOWNED placed/route-held (dsdv_slice c1x/c3x/lepe/lepw, s81sl_kv_leaf t1/t4, s81sl_leaf t1/36/55-57/60/62/66/68/72) + s81sl_leaf__t37 FAILED other flow error UNOWNED.
  S81 old: col_h9_r0_p1 STALE 9.5h; dsdv_slice_kv512_C__t1 DEAD-OWNER.
  QC new: cbf_q01_s2, sle_hc0 UNOWNED; slw_su_l1 DEAD-OWNER (FABLE-PD-QC-0945); 3 FAILED global_place/place (sle_st_a_v2, slw_st_a_v1, slw_st_b_v2) no relaunch, FAIL-ROUTE-1115.
  KV: new kv3_pc__cl5a95b461 FAILED PDN-0006 no relaunch; old kv3_pc_v1, kv3_pv_v8 6.7h, qkd_pv_fin_s8_pin. HEAD none.
- 2026-11-20 13:50 PST 13:50 sweep: 94 flagged (12 ROUTE-RELEASE-1300 held kits counted owned: S81-SLICEC-R3 4, S81-DIE-R4 7, QC-PLAN-R5 1).
  S81: 52 UNOWNED, nearly all new: s81sl_leaf/kv_leaf rows now state held by die owner (plan event pending) with no lane naming them (S81-DIE-R4 to claim); 1 DEAD-OWNER s81sl_leaf__t25__cl431c660f.
  QC: 8 new FAILED global_place no relaunch (FAIL-ROUTE-1115) + 2 old stale/place; 5 UNOWNED (sle_fw_v2, sle_sc_v2, sle_st_a_v1__cled3c1d7b, slw_hc2__cl6bcaba89, slw_st_b_v2__pv3d7bec84); 4 DEAD-OWNER (QC-PLAN-R4, UNIFY-TOOLS-R2 x2, CODEX-CROSS-HANDBACK-1120).
  KV: 22 WAIT-BIND, 6 FAILED-NO-RELAUNCH (new: CLAND ring band; kv3_pv_v8 7.xh, 7.4h hub stale); 10 new held/placed rows.
  HEAD: none flagged.
- 2026-11-20 14:50 PST 14:50 sweep: 495 rows, 35 flagged (was 94), 0 UNOWNED, 0 DEAD-OWNER after COORD owner mapping (S81-DIE-R4 leaf/kv_leaf, QC-PLAN-R5 QC, KV-PLAN-R1 hgi/hub/sys, AUTO-REVIEW-HELD listed owners).
  S81: none flagged. HEAD: none.
  QC: 15 FAILED-NO-RELAUNCH global_place (5 new, 10 old; 3 STALE) + 1 place error UNCLASSIFIED STALE; owner QC-PLAN-R5 (FAIL-ROUTE-1115).
  KV: 4 FAILED-NO-RELAUNCH (PDN-0006 x2, bind stale, flow errors; CLAND ring band), 19 WAIT-BIND held/placed; all old, owner KV-PLAN-R1.
  New since 13:50: only 5 QC global_place failures.
- 2026-11-20 15:50 PST 15:50 sweep (14:50 mapping + new COORD owners): 495 rows, 37 flagged (was 35).
  S81: 3 new UNOWNED placed/route-held: dsdv_slice_lepe_nh_mus_LP__t1, eng__t1, iqf__t1. HEAD hd_lep0N running 19h, owner FABLE-FIX-HEAD-LEP0N, not flagged.
  QC (QC-PLAN-R5): 15 FAILED-NO-RELAUNCH global_place (9 STALE, all old) + place error stale; 1 new other flow error sle_su_l1__cl5ea486db.
  KV (KV-PLAN-R2): 8 FAILED-NO-RELAUNCH (2 new: kv3_hub_C kit input missing, kv3_pc_v1__cl4ea58a5c/cl7f648944 flow errors; kv3_hub_Wi stale 9.4h) + 9 held WAIT-BIND (1 new).
  No DEAD-OWNER rows.
- 2026-11-20 16:51 PST 16:50 sweep (15:50 mapping + t2/t10/t52, reset-reach, AUTO-REVIEW-HELD owner column): 495 rows, 35 flagged (was 37), 0 DEAD-OWNER.
  S81: 1 new UNOWNED placed/route-held seqhost__t1; the 3 prior UNOWNED (lepe_nh_mus_LP t1, eng t1, iqf t1) cleared or mapped.
  QC (QC-PLAN-R5): 14 FAILED-NO-RELAUNCH global_place/place (13 STALE, old) + sle_su_l1 flow error old; new STALE cancelled sle_hc0__cl929603c0__cl38badc56.
  KV (KV-PLAN-R2): 8 FAILED-NO-RELAUNCH (new: kv3_pc_v1__cl4ea58a5c flow error) + 8 held WAIT-BIND, all else old.
  HEAD none flagged; reset-reach types (cbx_q10, kv3_pv_v2, lepe mu_LP t2/nh_mus t1) owned by RESET-RELAY-GEN-1530.
- 2026-11-20 17:51 PST 17:50 sweep (16:50 mapping + J6/leaf/svc/QC-PLAN-R6/HEAD R2 owners): 495 rows, 35 flagged (unchanged), 0 UNOWNED, 0 DEAD-OWNER.
  S81: 1 new, serdes__t4 FAILED detail_place no relaunch (owner: S81-DIE-R4 (+MERGE-QUEUE-1,CORE-LIB-LIMITS-1330)	yes). All J6/leaf/svc held rows mapped, none flagged.
  QC (QC-PLAN-R6): 14 held-by-die-owner STALE (formerly global_place failures), 1 place error UNCLASSIFIED STALE, 1 cancelled STALE; all old.
  KV (KV-PLAN-R2): 9 FAILED-NO-RELAUNCH (PDN-0006 x2, CLAND, bind stale, input missing, flow errors) + 9 held/cancelled WAIT-BIND; all old.
  HEAD none flagged.
- 2026-11-20 18:50 PST 18:50 sweep (17:50 mapping + SVC-R4, BKSEL-R4, KV-PV-R3, RESET-RELAY-GEN-R2, serdes t3/t4): 495 rows, 36 flagged (was 35); PLACE-SETUP-STOP rows 0.
  S81 new: col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760 FAILED CLAND ring band UNOWNED; ...__pvcb7f0079 same class FAILED-NO-RELAUNCH. serdes__t4 cleared.
  QC (QC-PLAN-R6): 16 STALE, all old (14 held, 1 place error, 1 cancelled).
  KV (KV-PLAN-R2/OPUS-FIX-KV-PV-R3): 8 FAILED-NO-RELAUNCH + 9 WAIT-BIND held/cancelled, all old.
  HEAD none flagged; 0 DEAD-OWNER.
- 2026-11-20 19:51 PST 19:50 sweep (18:50 mapping + S81-DIE-R5, QC-PLAN-R7, FABLE-FIX-QC-CB, KV HGI/PV-R4, HEAD owners): 494 rows, 37 flagged (was 36); PLACE-SETUP-STOP rows 0; 0 UNOWNED, 0 DEAD-OWNER.
  S81: 1 new STALE, serdes__t3 held by die owner (S81-DIE-R5). The two cl0cd90c0e CLAND rows cleared.
  QC (QC-PLAN-R7): 16 STALE held/cancelled (1 new: slw_su_c__cl92142dac); the unclassified place error cleared.
  KV: 9 FAILED-NO-RELAUNCH WAIT-BIND (1 new: kv3_io_cor_v1 detail route error) + 10 held/cancelled WAIT-BIND (1 new: kv3_sys_c placed, route held).
  HEAD none flagged.
- 2026-11-20 20:50 PST 20:50 sweep (19:50 mapping; HEAD-PLAN-R16, CORE-PIN-RELAY-R2 live; R15/1930/LOCKUP-1130/KV-PV-R3/FLEET-WATCH-1630 not used as owners): 483 rows, 32 flagged (was 37), 0 UNOWNED, 0 DEAD-OWNER.
  S81: 12 STALE held-for-plan-event rows, 11 new, all owned (S81-DIE-R4/R5, S81-J6-ASSEMBLY, RESET-RELAY-GEN-R2): leaf cl0cd90c0e pvcb7f0079, slice kv512_C t1, iqf t1, slice_station t36, iq_C t1, seqhost t1, 4 lepe/lepw LP rows, col_h10_r1 cl95b37463.
  QC (QC-PLAN-R7): only 1 STALE cancelled-superseded left; 15 held rows cleared.
  KV (KV-PLAN-R2): 9 FAILED-NO-RELAUNCH + 9 held/cancelled WAIT-BIND, all old, none new.
  HEAD: hd_lep0N running, not flagged.
- 2026-11-20 21:51 PST 21:50 sweep (new owners KV-PLAN-R3, QC-PLAN-R8, S81-BKSEL-R5, FABLE-FIX-S81-LEAF; lepe LP -> S81-DIE-R5): 483 rows, 154 flagged; 138 are STOOD-DOWN-OWNER (primary owner a stood-down lane), 0 UNOWNED, 0 DEAD-OWNER.
  STOOD-DOWN-OWNER by owner: BUILD-SETTINGS-AUDIT-1900 56, CORE-PIN-RELAY-R2 49, KV-PLAN-R2 5, FABLE-FIX-QC-CB 3, QC-PLAN-R7 2, LOCKUP-STATION-1130 2, OPUS-FIX-KV-PV-R3 1, S81-LEAF-CLASS-1730 1 (S81 85, KV 19, QC 15); needs reassignment to live lanes.
  S81 STALE held-for-plan-event: 16 (4 new). QC: 1 STALE cancelled old. KV real: 2 FAILED-NO-RELAUNCH + 15 held + 1 cancelled WAIT-BIND, old.
  HEAD: none flagged.
- 2026-11-20 21:51 PST CORRECTION to 21:50 sweep: STOOD-DOWN-OWNER rows are 119 (S81 85, KV 19, QC 15), not 138; 35 other flagged rows; total 154 of 483.
- 2026-11-20 21:53 PST 21:55 CORRECTED 21:50 sweep: mapping fixed (review/audit/tool lanes never own; default die lane S81-DIE-R5 / leaf FABLE-FIX-S81-LEAF / QC-PLAN-R8 / KV-PLAN-R3 / HEAD-PLAN-R16; stood-down -> successor). 483 rows, 37 flagged, 0 STOOD-DOWN-OWNER, 0 UNOWNED, 0 DEAD-OWNER.
  Primary-owner remaps: BUILD-SETTINGS-AUDIT-1900 and CORE-PIN-RELAY-R2 rows -> S81-DIE-R5 (83) or core-lib lane; KIT-WAVE(auto)/UNIFY-TOOLS-R3/PRECHECK QC rows -> QC-PLAN-R8; blank-owner S81 leaf rows -> FABLE-FIX-S81-LEAF (56). lanes/LANE-STATUS.tsv not yet present, built-in successor table used.
  S81: 16 STALE held-for-plan-event, all old, owned. QC: 1 STALE cancelled. KV: 2 FAILED-NO-RELAUNCH + 15 held + 2 placed/held + 1 cancelled WAIT-BIND, KV-PLAN-R3.
  HEAD: none flagged.
- 2026-11-20 22:51 PST 22:50 sweep (LANE-STATUS successors, tool/review lanes never own, HEAD owners lep0N/serdes): 489 rows, 48 flagged (was 37), 0 STOOD-DOWN-OWNER, 0 UNOWNED, 0 DEAD-OWNER.
  S81 new: 3 FAILED-NO-RELAUNCH (2 detail_place, 1 hold after CTS STALE) + 7 STALE held-for-plan-event; 16 old STALE held. Owners S81-DIE-R5/leaf/J6.
  QC (QC-PLAN-R8): 1 new FAILED global_place no relaunch; 1 old STALE cancelled.
  KV (KV-PLAN-R3): 1 new FAILED other flow error + 2 old FAILED + 15 held + 1 placed + 1 cancelled WAIT-BIND.
  HEAD: hd_lep0N running (OPUS-FIX-HEAD-LEP0N-R2), not flagged.
- 2026-11-20 23:51 PST 23:50 sweep, family-lane mapping (FAM-*, LANE-STATUS successors) + new route_hold_reason column (WAIT-VISUAL flagged): 489 rows, 59 flagged (was 48), 0 UNOWNED/DEAD-OWNER/STOOD-DOWN-OWNER.
  S81: 29 STALE held-for-plan-event (COL 9, SLICE 6, LEAF-R2 7, LEPE 2, MISC 3, SERDES 1; 5 new) + col hold-after-CTS FAILED-NO-RELAUNCH STALE (old); 4 WAIT-VISUAL (3 held rows + 1 NOT-IN-PLAN phy-class MISC row).
  QC: 5 new STALE held FAM-QC-CB, 1 old STALE cancelled FAM-QC-HCST, 1 new WAIT-VISUAL FAM-QC-HCST.
  KV: 2 FAILED-NO-RELAUNCH + 1 old FAILED bind stale (PV-R4) + 16 held/placed/cancelled WAIT-BIND; 1 new WAIT-VISUAL FAM-KV-HUB.
  HEAD: none flagged. KV-PLAN-R4 not used as a row owner (no uncategorised KV rows).
- 2026-11-20 23:52 PST CORRECTION 23:50: S81 STALE held-for-plan-event rows are 28 (COL 9, SLICE 6, LEAF-R2 7, LEPE 2, MISC 3, SERDES 1), not 29; totals S81 30, QC 7, KV 22 = 59 flagged.
