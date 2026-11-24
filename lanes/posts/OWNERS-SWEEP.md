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
- 2026-11-21 00:51 PST 00:50 sweep, family-lane mapping (QC-SLE-R3, HEAD-SERDES-R3): 489 rows, 54 flagged (was 59), 0 UNOWNED/DEAD-OWNER, nothing new since 23:50; held-for-plan-event rows counted owned by their family lane.
  S81 28 STALE held (COL 9, LEAF-R2 7, SLICE 6, LEPE 2, MISC 3, SERDES 1; 3 also WAIT-VISUAL) + FAM-S81-COL hold-after-CTS FAILED-NO-RELAUNCH STALE; 0 new.
  QC: 5 STALE held FAM-QC-CB + 1 STALE cancelled FAM-QC-HCST; the QC WAIT-VISUAL and NOT-IN-PLAN rows cleared.
  KV: 3 FAILED-NO-RELAUNCH (PV-R4 bind stale, FAM-KV-HUB, FAM-KV-IOPC) + 16 held/cancelled WAIT-BIND; all old.
  HEAD none flagged. Context well below 330k, no stand-down.
- 2026-11-21 01:53 PST 01:50 sweep with Fable-limit renames (OPUS-FIX QC-SLE-R4, KV-HGI-R3, S81-SVC-R5, S81-LEAF-R3, HEAD-SERDES-R4/LEP0N-R3, FAM-S81-COL-R2, FAM-QC-FEFW): 489 rows, 61 flagged (was 54), 0 UNOWNED/DEAD-OWNER.
  S81 (34): 5 new FAILED-NO-RELAUNCH (2 SERDES, LEAF-R3 stale, BKSEL-R5, ...) + old COL-R2 hold-after-CTS; 28 STALE held-for-plan-event (1 new SLICE), 3 WAIT-VISUAL.
  QC (6): 5 STALE held FAM-QC-CB + 1 STALE cancelled HCST, all old; none on SLE-R4/FEFW.
  KV (21): 4 FAILED-NO-RELAUNCH (1 new FAM-KV-HUB flow error) + 17 held/cancelled WAIT-BIND (1 new cancelled IOPC).
  HEAD none flagged (hd_lep0N running, LEP0N-R3). Context well below 330k.
- 2026-11-21 01:54 PST CORRECTION 01:50: S81 new FAILED-NO-RELAUNCH rows are 4 (FAM-S81-SERDES 2, OPUS-FIX-S81-LEAF-R3 1 stale, S81-BKSEL-R5 1), not 5; totals S81 34, QC 6, KV 21 = 61.
- 2026-11-21 03:39 PST 03:50 RESUME sweep (family mapping unchanged; Codex-started units already sit under family lanes, no extra owners needed): 495 rows, 72 flagged on spec flags (+84 rows carry the tool CBC-FALLBACK info flag only, S81 leaf/svc), 0 UNOWNED/DEAD-OWNER.
  S81: 9 FAILED-NO-RELAUNCH (5 new: COL-R2 x3, SERDES, LEAF-R3 CBC) + 28 STALE held-for-plan-event, all old.
  QC: 5 STALE held CB + 2 STALE cancelled + 1 STALE signed-count-pending (SLE-R4, new).
  KV: 9 FAILED-NO-RELAUNCH (5 new: PDN-0006 IOPC, HGI-R3 x3, PV-R4) + 17 held/cancelled WAIT-BIND.
  HEAD none flagged. Context well below 330k.
- 2026-11-21 03:40 PST CORRECTION 03:50: S81 STALE held-for-plan-event rows are 29 (not 28); S81 38 + QC 8 + KV 26 = 72 flagged.
- 2026-11-21 03:50 PST OWNERS-SWEEP hourly (QC-PLAN-R9, FAM-S81-COL-R3; CBC-FALLBACK informational): 494 rows, 75 flagged on spec flags (+84 CBC-only), 0 UNOWNED/DEAD-OWNER; new column failed_disposition.
  FAILED-NO-RELAUNCH 18 rows: 14 ORPHANED (S81 col 4+hold-after-CTS, serdes 2, leaf 2; KV hgi_v3/v5/v8, hub_Wi, sys_c, pv_v8), 4 DELIBERATE by family-lane post (KV kv3_io_cor_v1, kv3_pc_v3, kv3_pv; S81 bk_sel__t2). Heuristic: keyword + item name in the family lane post, last 12 h.
  S81: 29 STALE held-for-plan-event, all old; QC: 5 STALE held CB + 4 STALE cancelled (2 new: FEFW, QC-PLAN-R9); KV: 17 held/cancelled WAIT-BIND (2 new cancelled HGI-R3).
  HEAD none flagged (hd_lep0N, LEP0N-R3).
- 2026-11-21 03:51 PST CORRECTION: KV held/cancelled WAIT-BIND rows are 19 (not 17); totals S81 38, QC 9, KV 28 = 75.
- 2026-11-21 04:52 PST OWNERS-SWEEP hourly (col split H9R0/H10/R3, SLICE-R2, MISC-R2, KV-HUB-R2, LEP0N-R4): 491 rows, 53 flagged, 0 UNOWNED/DEAD-OWNER, CBC-FALLBACK rows 0; failed_disposition kept.
  S81 13 (was 38): 11 new STALE cancelled-superseded col rows (H9R0 9, H10 2) + 2 old STALE held H9R0; all S81 FAILED/leaf/serdes/slice held rows cleared.
  FAILED-NO-RELAUNCH 9, all KV: 9 DELIBERATE (HOLD posts 03:52 by HGI/HUB lanes; IOPC 23:54 census; pv D28; pv_v8 on cancel list), 0 ORPHANED.
  QC 14: 5 STALE held CB, 4 STALE cancelled, 3 new WAIT-VISUAL HCST (+2 STALE cancelled counted); KV 26 WAIT-BIND: 9 FAILED + 17 held/cancelled.
  HEAD none flagged (LEP0N-R4). Note: CANCEL-SWEEP-0450 has no post file; cancels matched via CANCEL-GRT-FLAT/UNSIGNABLE tsv only.
- 2026-11-21 04:53 PST CORRECTION: counts are S81 13, QC 12 (5 STALE held CB + 4 STALE cancelled + 3 WAIT-VISUAL HCST), KV 28 (9 FAILED + 19 held/cancelled) = 53.
- 2026-11-21 05:52 PST OWNERS-SWEEP hourly (refreshed lane map: COL-R4/H9R0-R2/H10-R2, SLICE-R3, SERDES-R3, LEPE-2, SVC-R6, KV-HGI-R4/PV-R5, FABLE-FIX KV-HUB/LEAF-R3/HEAD-LEP0N): 489 rows, 31 flagged (was 53), 0 UNOWNED/DEAD-OWNER, 0 FAILED-NO-RELAUNCH.
  S81 21 STALE: 19 cancelled-superseded (SVC-R6 7 new, H9R0-R2 10 incl 1 new, H10-R2 2) + 2 held H9R0-R2; all FAILED/leaf/serdes/slice rows gone.
  QC 9 STALE: 5 held FAM-QC-CB + 4 cancelled (FEFW, HCST, SLE-R4, QC-PLAN-R9); 3 WAIT-VISUAL HCST cleared.
  KV 1 WAIT-BIND cancelled (PV-R5); the 27 held/failed KV rows no longer flagged. HEAD none.
  FABLE-FIX-S81-COLROM owns lever work, not a row family, so no rows mapped to it.
- 2026-11-21 06:51 PST OWNERS-SWEEP hourly 07:50 (LANE-STATUS chains applied; QC-PLAN-R10, FABLE-FIX-KV-HUB-R2, S81-LEAF-R5, LEPE-3): 490 rows, 33 flagged (was 31), 0 UNOWNED, 0 CBC-FALLBACK.
  FAILED-NO-RELAUNCH 1: QC cbn_q01__clab6e67f2 (FAM-QC-CB, STALE, new) ORPHANED, no deliberate hold/cancel post.
  S81 21 STALE, all old: 19 cancelled-superseded (SVC-R6 7, COL-H9R0-R2 10, COL-H10-R2 2) + 2 held H9R0-R2.
  QC 11: 5 held CB + 1 new cancelled CB + 4 old cancelled (FEFW, HCST, SLE-R4, QC-PLAN-R10) + the failed row; KV 1 cancelled WAIT-BIND; HEAD none.
  Family lane QC-PLAN-R10 shows no post in 2 h (owns 1 row, DEAD-OWNER by that test); the rest of the family lanes posted.
- 2026-11-21 07:51 PST OWNERS-SWEEP hourly 08:50 (chains: TAP-GRID/FLEET-WATCH n/a, LEP0N-R2, COL-H10-R3 via LANE-STATUS): 490 rows, 60 flagged on spec flags (+3 CBC-only), was 33; 0 UNOWNED.
  FAILED-NO-RELAUNCH 4 (all new but QC CB-R2): 1 ORPHANED (KV kv3_hgi_v8, HGI-R5), 3 DELIBERATE (KV kv3_hub_Wo waiter-fail answer; QC cbn_q01 takeover post; QC slw_st_a_v2 cancel list) + 1 QC FAILED HCST new.
  S81 41 STALE: 35 cancelled-superseded (COL-H9R0 14, SVC-R6 12, COL-H10 7, LEAF-R5 2, SLICE-R4 1, BKSEL 1) + 3 held + 1 signed-count-pending (many new).
  QC 16 STALE (5 held CB-R2, 6 cancelled, 3 signed-count-pending new); KV 1 cancelled WAIT-BIND.
  Lanes with no post <2h: FABLE-FIX-HEAD-LEP0N-R2 (no post file, owns hd_lep0N, running, not flagged), FAM-QC-HCST, OPUS-FIX-QC-SLE-R4.
- 2026-11-21 07:51 PST CORRECTION 08:50: S81 cancelled-superseded rows are 37 (COL-H9R0 14, SVC-R6 12, COL-H10 7, LEAF-R5 2, SLICE-R4 1, BKSEL 1), S81 total 41; the FAILED-NO-RELAUNCH count is 4 in total (the QC HCST failed row is one of the 3 deliberate/QC ones, not an extra).
- 2026-11-21 08:53 PST 0900 sweep: 488 rows (S81/HEAD/QC/KV, HBM skipped); tool flagged 156, 147 are signed-count-pending 4 / held-for-plan-event 92 / cancelled-superseded 51 (counts only); 9 real flags.
  Real KV 5: FAILED-NO-RELAUNCH 3 (kv3_hg_v1, kv3_hgi_v8, kv3_hub_Wo), FAILED other flow error 2 just now (kv3_hg_v1p3, kv3_hg_v1p4); owners alive (FAIL-ROUTE-1115 posted 08:48).
  Real QC 4: FAILED-NO-RELAUNCH 3 (cbn_q01__clab6e67f2 also STALE 5.2h, sle_ctl__cla4f6f12f, slw_st_a_v2__clf4365a62), CBC-FALLBACK running 1 (slw_st_a_v2__cl9f076a5c); owners alive.
  S81 0 real flags, HEAD 0 rows, UNOWNED 0, DEAD-OWNER 0 (all S81 UNOWNED 74 / DEAD-OWNER 15 / STALE rows are held or cancelled). Successor lanes (11 listed) already in agent_ids.
  Details lanes/OWNERS-SWEEP.tsv
- 2026-11-21 09:56 PST 0950 sweep: 487 rows (S81/HEAD/QC/KV; HBM skipped), lanes/OWNERS-SWEEP.tsv. After family-lane coverage: 0 S81 UNOWNED/DEAD-OWNER (113 rows covered by live FAM-S81-COL-H10-R3/H9R0-R3/SLICE-R4/MISC-R3, FAM-QC-CB-R2). KV: 7 FAILED-NO-RELAUNCH (kv3_hg_v1,v1p3,v1p4,hgi_v8,hub_Wo,pv_v2n,pv_v8), 2 UNCLASSIFIED, 2 CBC-FALLBACK (kv3_hub_Wi, kv3_pc_v3). QC: 3 FAILED-NO-RELAUNCH (cbn_q01__clab6e67f2, sle_ctl__cla4f6f12f, slw_st_a_v2__clf4365a62), 2 UNOWNED (sle_stm_v2__cl7b3062fa, slw_hc2__cla3497502__cl16607c7a). HEAD clean. KV core qkd_pv_fin_s8_pin superseded, unowned.
- 2026-11-21 10:53 PST 11-21 10:55 sweep: 484 rows S81/HEAD/QC/KV (HBM skipped). Family post-pass cleared UNOWNED/DEAD-OWNER on 139 rows (98 S81 UNOWNED + 30 S81 + 11 QC DEAD-OWNER) via live family lanes. Remaining: KV FAILED-NO-RELAUNCH 10 (hg_v1,v1p2,v1p5,v1p6, pv_v12,v2,v2n,v3,v4,v7), QC FAILED-NO-RELAUNCH 2, CBC-FALLBACK KV 2/QC 2. STALE>3h: S81 49, QC 26 (mostly held/cancelled/signed count pending). Unowned 0, dead-owner 0 after post-pass.
- 2026-11-21 11:56 PST OWNERS-SWEEP 12:00: 469 unsigned rows (S81 348, QC 70, KV 50, HEAD 1); 286 HELD-EVENT (J7), not flagged.
  S81 UNOWNED 28 non-held (svc_lo/svc_hi_dsdv_svc*, dsdv_slice_c3x/lepe, s81sl_leaf t52): all cancelled-superseded, stale 6-10 h; closest lane S81-DIE-R5.
  S81 STALE 36 cancelled-superseded col_h9_r0*/col_h10_r*/bk_sel: owners FAM-S81-COL-R5/H10-R3/H9R0-R3 alive; S81 DEAD-OWNER 2 (s81sl_leaf__t28, dsdv_slice_kv512_C__t1: S81-DIE-R5 silent).
  KV FAILED-NO-RELAUNCH 10: kv3_pv_* (CLAND ring band, over 400k) -> OPUS-FIX-KV-PV-R5/TAP-GRID-R3; kv3_hg*/hg_v1p5/v1p6 -> OPUS-FIX-KV-HGI-R5.
  HEAD 1 hd_lep0N running (FABLE-FIX-HEAD-LEP0N-R2); QC 70 all clean.
- 2026-11-21 12:53 PST 1400 sweep: 469 unsigned rows S81/HEAD/QC/KV (HBM skipped); 296 HELD-EVENT (unflagged).
  S81 flagged: STALE ~50 (superseded col/svc/leaf, owners FAM-S81-COL-*/OPUS-FIX-S81-SVC-R8), UNOWNED 9 (svc_hi 8 -> SVC-R8, s81sl_kv_leaf__t1), FAILED-NO-RELAUNCH serdes__t12.
  KV: FAILED-NO-RELAUNCH 16 (pv/hg/hgi, owners PV-R5/HGI-R6); kv3_sys_c unclassified; CBC-FALLBACK 2 held.
  HEAD: hd_lep0N FAILED-NO-RELAUNCH (FABLE-FIX-HEAD-LEP0N-R2). QC: cbf_q01_s2 DEAD-OWNER (FAM-QC-CB-R2), tt_ctlm + slw_stm_v2 UNOWNED.
  File lanes/OWNERS-SWEEP.tsv committed.
- 2026-11-21 18:28 PST OWNERS-SWEEP-1900 [OWNERS-SWEEP -> COORD] 463 rows rebuilt (lanes/OWNERS-SWEEP.tsv, commit 17ed5c1c38).
  S81: 132 UNOWNED/62 STALE were held J7 plan-event or superseded-cancelled rows; reclassified HELD/CANCELLED with inferred owners, no real flags left.
  HEAD: hd_lep0N FAILED place, stale 8.6h, owner FABLE-FIX-HEAD-LEP0N-R2 alive (18:16), no relaunch.
  KV: hg/pv failed rows HELD (D27d3 green, D28); kv3_hroot owner R3 dead (12:37) -> R4; kv3_hg_v1p2 owner FLOW-CLKGRT-R2 dead (15:53).
  QC: 4 FAILED no relaunch, stale 4-5h (cbf_q00_s2, cbx_q10, sle_stm_v1, slw_su_c); owners alive.
- 2026-11-21 18:52 PST 18:5x sweep: lanes/OWNERS-SWEEP.tsv 463 rows (S81 347, QC 65, KV 51, HEAD 1), committed.
  S81: 141 UNOWNED (col_h9/col_h10 held-by-die-owner twins, plan event pending), 62 STALE mostly superseded-cancelled; serdes__t12 HOST-BLOCKED.
  QC: 11 cbn/cbf no-host rows + 2 INFRA fails HOST-BLOCKED; 5 FAILED-NO-RELAUNCH other flow error (cbf_q00_s2, cbx_q10, slw_su_c); 5 STALE.
  KV: 10 FAILED-NO-RELAUNCH (kv3_pv_v* CLAND ring band/400k cells, kv3_hroot dead owner); 22 WAIT-BIND; 2 CBC-FALLBACK (hub_Wi, pc_v3).
  HEAD: hd_lep0N failed place 9 h, owners alive, no relaunch.
- 2026-11-21 19:50 PST 469 rows (S81 348, QC 70, KV ~50, HEAD 1; HBM skipped)
  flagged: S81 UNOWNED 134 + STALE 64 (mostly held-by-die-owner / cancelled-superseded col_h9/h10 variants); QC FAILED-NO-RELAUNCH 5, STALE 5, DEAD-OWNER 1 (native59)
  KV WAIT-BIND 24, CBC-FALLBACK 2 (kv3_hub_Wi, kv3_pc_v3), FAILED-NO-RELAUNCH 1 (kv3_hroot); HEAD hd_lep0N FAILED-NO-RELAUNCH+STALE
  top classes: held by die owner 288, running 67, cancelled superseded 59+, FAILED no host 12, other flow error 6
  revoked counted unsigned per tool; tool bin/owners_sweep.py
- 2026-11-21 20:53 PST 20:50 sweep 469 rows, 215 clean. S81: 105 HELD-EVENT (J7 04:14, owner S81-J7-HELD-R1), 12 UNOWNED cancelled-superseded col_h9/h10, 60 DEAD-OWNER (FAM-S81-COL-R5 57), 64 STALE.
  QC: 2 UNOWNED (cbn_q11 x2, route held), 2 DEAD-OWNER (cbf_q01, slw_stm_v2), 3 FAILED-NO-RELAUNCH, 6 STALE.
  KV: 2 FAILED-NO-RELAUNCH (kv3_hroot owner FAM-KV-HROOT-R1, kv3_hub_Wo), 16 WAIT-BIND under KV-WAITBIND-R1, 2 CBC-FALLBACK.
  HEAD: hd_lep0N FAILED-NO-RELAUNCH+STALE 11h, owner FABLE-FIX-HEAD-LEP0N-R7 live.
  COORD-ROUTED-OWNERS.tsv is in autopilot/, not coord root.
- 2026-11-21 21:51 PST 21:50 sweep: 467 unsigned rows (S81 348, QC 68, KV ~50, HEAD 1). Flags: S81 UNOWNED 43, DEAD-OWNER 19 (18 S81-GEOM-OPUS col_h10_r2, 1 SLICE-R5), STALE 65. QC FAILED-NO-RELAUNCH 4, STALE 8. KV FAILED-NO-RELAUNCH 3 (hroot, pc_v3, hub_Wo), 15 WAIT-BIND (owned-held). HEAD hd_lep0N FAILED-NO-RELAUNCH+STALE 11h (R7 alive). Table lanes/OWNERS-SWEEP.tsv.
- 2026-11-21 22:50 PST 22:50 sweep 463 rows (S81 347, QC 67, KV 48, HEAD 1; HBM skipped); 63 superseded rows not flagged.
  S81: 32 UNOWNED held-by-die-owner (col_h9_r0_p6 x11, dsdv_slice_c1x_C x9, s81sl_kv_leaf x3, dsdv_slice_lepw/lepe/iq, svc_hi_dsdv_svc); 10 col_h9_r0_p4/p5 DEAD-OWNER (S81-GEOM-OPUS).
  QC: FAILED-NO-RELAUNCH cbx_q10__cl89936551_h, slw_su_c__cl19bb38ef, slw_su_c__cl92142dac (FAM-QC-SLWSLE-R1); cbn_q01 DEAD-OWNER.
  HEAD: hd_lep0N FAILED-NO-RELAUNCH, stale 13h (FABLE-FIX-HEAD-LEP0N-R7 alive). KV: kv3_hub_C kit_rtl UNCLASSIFIED.
  File lanes/OWNERS-SWEEP.tsv committed.
- 2026-11-21 23:50 PST 23:50 sweep 461 rows (S81 347, QC 65, KV 48, HEAD in S81 set); 366 unflagged.
  KV FAILED-NO-RELAUNCH 5: kv3_hub_Wo, kv3_io_cor_v1, kv3_pc_v1 x3 (cl23f6a148, cl7f648944, cl4ea58a5c).
  QC FAILED-NO-RELAUNCH 4: cbx_q10 (cl89936551_h, cl94a12200_h), slw_su_c (cl19bb38ef, cl92142dac), 3 stale.
  S81 UNOWNED held 17: dsdv c1x t3-t10, iq, lepw (mu, mus, LP) -> FAM-S81-DSDV-R1; s81sl_kv_leaf t3/t4, svc_hi pvso_entry t2, svc_hi rs t5 unowned.
  S81 col held STALE 5 (live FAM owners, not flags); superseded rows omitted.
- 2026-11-22 00:51 PST 01:0x sweep 221 unsigned s81/head/qc/kv rows: HELD-OK 87 (s81 79, kv 8), flagged 76 (DEAD-OWNER 33, STALE 48, UNOWNED 0, FAILED-NO-RELAUNCH 0; some both). s81: FAIL-S81-1 has 20 rows with no post in 2h (6 superseded-await-relaunch stale); S81-CORES 4 cores idle 20h+ no post; OPUS-FIX-S81-LEAF-R10 18 leaf superseded rows stale >3h. kv: KV-R owns 7 hgi/hub_Wo rows with no post (kv3_hub_Wo FAILED); KV-CORES 3 qkd cores dead. qc: 7 qfd_qc_su_lane_w KIT-PLACED PASS kits not enqueued (QC-PLAN); GEOM-UNHOLD-2200 and FABLE-FLOW-2000 no posts. File lanes/OWNERS-SWEEP.tsv
- 2026-11-22 02:27 PST OWNERS-SWEEP 02:26: 461 unsigned rows (S81 347, QC 64, KV 49, HEAD 1); no UNOWNED, no DEAD-OWNER (all owners alive).
  FAILED-NO-RELAUNCH 3: KV kv3_hub_Wo (OPUS-FIX-KV-HUB-R6), KV kv3_io_cor_v1 (FAM-KV-IOPC-R4), QC slw_st_a_v2__cl9f076a5c (PRECHECK-1119).
  STALE 74: S81 68 (cancelled-superseded 62, held-by-owner 5, signed-pending 1), QC 6 (held 3, cancelled/withdrawn/signed-pending 3); owners live.
  KV WAIT-BIND 5 (KV-WAITBIND-R1 3 + the 2 failed); KV CBC-FALLBACK 2: kv3_pc__cl254f2e73, kv3_pc__cl5a95b461.
  4 unsigned types have no kit-wave row (S81 1, QC 2, KV 1). Table lanes/OWNERS-SWEEP.tsv.
- 2026-11-22 02:50 PST 02:50 sweep: 461 rows (HEAD/S81/QC/KV), 0 UNOWNED, 0 DEAD-OWNER (unchanged vs 02:26).
  Changes: KV FAILED-NO-RELAUNCH 2->3 (+kv3_pc__cl254f2e73, owner KV-PLAN-R6), KV CBC-FALLBACK 2->3, QC STALE 6->7.
  Still flagged: KV 3 failed (kv3_hub_Wo, kv3_io_cor_v1, kv3_pc__cl254f2e73), QC 1 failed (slw_st_a_v2__cl9f076a5c, FAM-QC-SLWSLE-R1), KV 5 WAIT-BIND.
  STALE: S81 68 (unchanged), QC 7. HEAD clean.
  377 rows no flag; file lanes/OWNERS-SWEEP.tsv
- 2026-11-22 03:50 PST OWNERS-SWEEP 03:5x: 460 rows (S81 347, QC 63, KV 49, HEAD 1); 84 flagged.
  S81: STALE 67 (cancelled-superseded old-plan pv rows, owners FAM-S81-COL-H9R0-R4/COL-H10-R4/SVC-R9/LEAF-R10 alive); UNOWNED 1 dsdv_slice_kv512_C__t1 (FAM-S81-SLICE-R6 mentions it).
  QC: STALE 6, FAILED-NO-RELAUNCH 2 (coll_core, slw_st_a_v2__cl9f076a5c; FAM-QC-SLWSLE-R1).
  KV: FAILED-NO-RELAUNCH 2 (kv3_hub_Wo, kv3_io_cor_v1), WAIT-BIND 6, CBC-FALLBACK 2; owners OPUS-FIX-KV-HUB-R6, FAM-KV-IOPC-R4, KV-WAITBIND-R1.
  No DEAD-OWNER rows; HEAD clean.
- 2026-11-22 04:51 PST 04:55 sweep 470 rows (S81 347, QC 63, KV 49, HEAD 1; HBM skipped).
  S81: 67 HELD-J8 (superseded/held col,leaf,svc under J7 typed holds), 9 UNOWNED (no kit-wave row), 1 DEAD-OWNER (s81_svc_idx_hslice_fp), 280 clean.
  QC: 6 HELD-V3, 2 FAILED-NO-RELAUNCH (coll_core, slw_st_a_v2__cl9f076a5c), 55 clean.
  KV: 2 FAILED-NO-RELAUNCH (kv3_hub_Wo, kv3_io_cor_v1), 8 WAIT-BIND, 2 CBC-FALLBACK, 40 clean.
  HEAD: hd_lep0N running (lint advisory); hd_ctl/host_e/host_n not in table (tool counts them signed).
- 2026-11-22 05:51 PST 05:50 sweep 468 rows: S81 147 HELD-J8, 10 SIGNED-LEC-PENDING, 0 flagged; QC 11 HELD-V3, 13 STALE (9 cancelled-superseded, coll_ftc withdrawn, cbx_q10 held x2, slw_su_c cl19bb38ef owner FIX-SYNC-KVHEAD), 2 FAILED-NO-RELAUNCH (coll_core, slw_st_a_v2__cl9f076a5c); KV 12 HELD-D28, 1 FAILED-NO-RELAUNCH (kv3_io_cor_v1 place FAM-KV-IOPC-R4); HEAD 0; UNOWNED 0 DEAD-OWNER 0
- 2026-11-22 06:51 PST 06:50 sweep (ec3c054): unsigned S81 353, QC 62, KV 48, HEAD 1 (HBM skipped).
  OK: S81 349, QC 29, KV 47, HEAD 1. UNOWNED 0.
  FAILED-NORELAUNCH: S81 3 (col_h9_r1__t1 pv1c15776f, s81sl_leaf__t31, dsdv_slice_lepe_nh_mus_LP__t1), QC 2 (coll_core, slw_st_a_v2__cl9f076a5c), KV 1 (kv3_hub_Wo).
  STALE: QC 27 (cancelled/held, 3-17h), S81 1 (slice_station__t52). DEAD-OWNER: QC 6 sle_hc1/sle_st_b/slw_fe rows, FLOW-FLEET-R1 last post 02:57.
  Held S81 147 / KV 38 / QC ~18 pending plan events are counted OK.
- 2026-11-22 07:51 PST 07:51 sweep 449 unsigned rows (S81 347, QC 52, KV 47, HEAD 1). OK 198. DEAD-OWNER 249 (S81 223 = LEAF-R10 66 last post 02:33, COLROM-R6 ~113 last 05:19, SVC-R9 14; KV 19 HGI-R6 02:48; QC 7). UNOWNED 0, FAILED 0, STALE 0. DEAD-OWNER = primary lane no post 2h; successor lanes often posting.
- 2026-11-22 07:52 PST 07:51 CORRECTION: S81 DEAD-OWNER 223 = COLROM-R6 118 (last 05:19), LEAF-R10 80 (02:33), SVC-R9 16 (04:15), FAIL-S81-1 6, DSDV-R1 2, COL-R6 1. Prior post split was wrong; totals unchanged.
- 2026-11-22 08:50 PST 09xx sweep: 458 unsigned rows (S81 349, QC 62, KV 47, HEAD 1); no UNOWNED.
  FAILED-NO-RELAUNCH 15, all S81: s81sl_leaf t2/t12/t31/t33/t44/t45/t47/t52 (OPUS-FIX-S81-LEAF-R10), col_h10_r2, col_h9_r2, dsdv_slice_lepe_mu_LP, lepe_nh_mus_LP, lepw_mu_C, lepw_mus_LP, iqf__t1.
  DEAD-OWNER 2, QC: cbn_q00 cl622f65d2 + cldbcda913 (TAP-GRID-R5, no post 2 h).
  STALE 1: S81 col_h9_r0_p6 (FAM-S81-COL-H9R0-R4).
  UNCLASSIFIED 3: KV kv3_hub_C (kit_rtl), QC slw_st_b_v1 cle6023ec2, S81 s81sl_leaf t65 (place error).
- 2026-11-22 09:51 PST 10xx sweep 458 rows (S81 349, QC 61, KV 47, HEAD 1). Flags: 6 FAILED-NO-RELAUNCH, 2 UNCLASSIFIED, 0 UNOWNED, 0 DEAD-OWNER, 0 STALE.
  S81 FAILED-NO-RELAUNCH: col_h9_r1 pv4bd36c74, col_h9_r2 pv7c30fd4e + pvdc7d4221 (OPUS-FIX-S81-COLROM-R6; bind_toolskew), leaf t1 + t65 (OPUS-FIX-S81-LEAF-R10; place fail, t65 UNCLASSIFIED).
  KV: kv3_hub_C kit_rtl FAIL UNCLASSIFIED (FAM-KV-HUBC-SYSC-R2; private kv3_sys_c running).
  QC, HEAD: no flags; cbn_q00 now FABLE-FIX-QC-V4.
  Read-only, nothing changed.
- 2026-11-22 10:51 PST 11-22 11:0x sweep, 458 rows, 7 flagged (447 clean): S81 UNOWNED 4 (svc_rs t3-6, relaunched prelint 10:45) + DEAD-OWNER 1 (pvso_entry__t1, S81-BKSEL-R7 last post 08:28). QC UNOWNED 2 (cbf_q01_s2, cbf_q11) + DEAD-OWNER 1 (slw_su_c__cl19bb38ef, TAP-GRID-R5). KV 0 flagged (hub_C held/retry D28; pc_v3 relaunched private kit, WAIT-BIND). HEAD 0. S81 leaf t1 held/retry J9 LEAF-R10. FAILED-NO-RELAUNCH 0, STALE 0, UNCLASSIFIED 0 after cuts.
- 2026-11-22 17:52 PST 21xx sweep: unsigned owned 100pct (S81 348, QC 56, KV 47, HEAD 1); 0 UNOWNED, 0 DEAD-OWNER after fixing FAM-QC-FEFW->R2/R3 id. S81 FAILED-NO-RELAUNCH 17 (LEAF-R10 11, COLROM-R6 2, SLICE-R6 2, COL-H10-R4 1, S81-DIE-R5 1); S81 STALE ~24 after svc/held filter (leaf, dsdv cancelled, col_h9_r2). QC STALE 1 sle_ctl__cla4f6f12f (cancelled, LOCKUP-STATION-R3). KV WAIT-BIND 4 + kv3_hub_C kit_rtl UNCLASSIFIED (KV-RINGMAC-R1). File lanes/OWNERS-SWEEP.tsv (tool bin/owners_sweep.py + post-filter).
- 2026-11-22 18:53 PST 18:50 sweep 451 unsigned rows (S81 348, QC 55, KV 47, HEAD 1; HBM skipped); 0 UNOWNED, 0 DEAD-OWNER.
  S81 FAILED-NO-RELAUNCH 26 (stale 3-10h): LEAF-R10 leaf t1/t8/t14-16/t24/t37/t53/t54/t74; SVC-R9 svc_rs t2-7, rs_w, pvso_entry t1/t2; SLICE-R6 lepe_mu_C, c1x_C t9; COLROM-R6 col_h9_r2 x2; COL-H10-R4 col_h10_r1.
  S81 held/cancelled-superseded rows with live owners (COL-H9R0-R4, SERDES-R7, LEAF-R10, COLROM-R6) filtered from STALE.
  KV: kv3_hub_C kit_rtl FAILED UNCLASSIFIED + WAIT-BIND (KV-RINGMAC-R1); WAIT-BIND 3 more (kv3_sys_c, kv3_pc_v3).
  QC 55 clean, HEAD hd_lep0N running. Read-only; lanes/OWNERS-SWEEP.tsv.
- 2026-11-22 18:53 PST 18:50 sweep 451 unsigned rows (S81 348, QC 55, KV 47, HEAD 1; HBM skipped); 0 UNOWNED, 0 DEAD-OWNER.
  S81 FAILED-NO-RELAUNCH 26 (stale 3-10h), all STALE: LEAF-R10 leaf t1/t8/t14-16/t24/t37/t53/t54/t74 (other flow error/congestion); SVC-R9 svc_rs t2-7,rs_w,pvso_entry t1/t2; SLICE-R6 dsdv_slice_lepe_mu_C, c1x_C t9; COLROM-R6 col_h9_r2 x2; COL-H10-R4 col_h10_r1 pv86f5e3b9.
  S81 STALE-only ~36 are held (plan event pending)/cancelled-superseded with live owners (COL-H9R0-R4, SERDES-R7, LEAF-R10, COLROM-R6); filtered from STALE.
  KV: kv3_hub_C FAILED kit_rtl UNCLASSIFIED + WAIT-BIND (KV-RINGMAC-R1); WAIT-BIND 3 more (kv3_sys_c, kv3_pc_v3). QC 55 clean, HEAD hd_lep0N running.
  Read-only; file lanes/OWNERS-SWEEP.tsv.
- 2026-11-22 19:51 PST 19:50 sweep 451 unsigned rows (S81 348, QC 52, KV 48, HEAD 1; HBM skipped); 0 UNOWNED, 0 DEAD-OWNER.
  S81 FAILED-NO-RELAUNCH 13 (was 22): LEAF-R10 11 (leaf t1/t8/t14-16/t24/t25/t37/t53/t54/t74, other flow error/congestion, 3-12h); COLROM-R6 col_h9_r2 pv6a2b031b (congestion 6.6h); S81-DIE-R5 lepe_nh_mus_LP t1 (NEW, 9h).
  SVC-R9 svc rows, col_h10_r1, dsdv c1x_C/lepe_mu_C now held for plan event with live owner, so OK; held/cancelled/relaunched STALE filtered.
  KV 0 flagged (was 4: kv3_hub_C kit_rtl cleared); QC sle_su_l1 place error 0.8h UNCLASSIFIED (PRECHECK-R2, new); HEAD hd_lep0N ok.
  Read-only; lanes/OWNERS-SWEEP.tsv.
- 2026-11-22 20:51 PST OWNERS-SWEEP 20:50: 448 unsigned rows (HEAD/KV/QC/S81, HBM skipped); 365 unflagged.
  UNOWNED 0, DEAD-OWNER 0 on all dies; S81 STALE-3H 77, FAILED-NORELAUNCH 18, UNCLASSIFIED 3; QC FAILED-NORELAUNCH 2 (sle_su_l1, slw_st_a_v2), UNCLASSIFIED 1; KV UNCLASSIFIED 1 (kv3_hub_Wo); HEAD clean.
  Top S81 groups: s81sl_leaf (OPUS-FIX-S81-LEAF-R10) ~27 stale + 14 failed; col_h9_r0_p (FAM-S81-COL-H9R0-R4) 14 stale+1 failed; col_h9_r rom (OPUS-FIX-S81-COLROM-R6) ~12 stale+3 failed.
  Next: svc_hi/lo dsdv_svc_rs (OPUS-FIX-S81-SVC-R9) 10 stale + 3 unclassified; serdes (FAM-S81-SERDES-R7) 5 stale; dsdv_slice_* ~9 stale (FAM-S81-SLICE-R6 etc).
  Table: lanes/OWNERS-SWEEP.tsv (tool bin/owners_sweep.py).
- 2026-11-22 21:50 PST 21:5x sweep (lanes/OWNERS-SWEEP.tsv, HBM skipped)
  S81: 35 STALE (11 are cancelled-superseded, no kit), 55 HELD-EVENT (J9/plan event, expected), 26 FAILED-NO-RELAUNCH (LEAF-R10 ~19, COLROM-R6 3, COL-H9R0-R4 2+), 1 DEAD-OWNER iqf__t1 (FAM-S81-DSDV-R1)
  QC: 2 FAILED-NO-RELAUNCH sle_su_l1__cl5ea486db (FAM-QC-SLWSLE-R1; place error, also UNCLASSIFIED), slw_st_a_v2__clf4365a62 (FAIL-ROUTE-1115; CLAND ring band)
  KV: 1 UNCLASSIFIED kv3_hub_Wo (OPUS-FIX-KV-HUB-R6, kit_rtl FAIL); HEAD clean
  New vs 20:50: S81 UNCLASSIFIED 3 -> 0, STALE 77 -> 35 (+55 re-marked HELD-EVENT), FAILED 18 -> 26, DEAD-OWNER iqf__t1 new
- 2026-11-22 22:51 PST 23:0x sweep 449 rows, 346 clean; Fable lanes mapped to Opus successors (KV-HG-R8, HEAD-LEP0N-R9, QC-V4-R2, KV-PV-SINKSPREAD-R2, KV-DIE-R2, S81 LEAF-TAPHOLD-R2, COL-RANKSEAT-R2); QC-RELAUNCH-R1 excluded; no DEAD-OWNER.
  S81: FAILED-NO-RELAUNCH 32 (leaf 24 other-flow/congestion, col_h9/h10 7, slice 1), STALE 96 (held 56, failed 32, cancelled 9), UNOWNED 2 (iqf__t1, dsdv_slice_lepe_nh_mus_LP__t1).
  QC: FAILED-NO-RELAUNCH 1 (sle_st_a_v1 CLAND ring band), STALE 1 (slw_st_a_v2 held, FAM-QC-SLWSLE-R1 live).
  KV: FAILED-NO-RELAUNCH 1 (kv3_pc_v1 global_place), UNCLASSIFIED 1 (kv3_hub_Wo kit_rtl, OPUS-FIX-KV-HUB-R6).
  HEAD: no flags. New VIS-*/LEAF-ROUTE-CBC lanes have no posts yet, not matched.
- 2026-11-22 23:50 PST 23:55 sweep: 449 rows (S81/HEAD/QC/KV), 0 UNOWNED, 0 DEAD-OWNER (VIS/plan owners honored).
  FAILED-NO-RELAUNCH 15: S81 7 (COL-H9R0-R4 2, LEAF-R10 2, COL-H10-R4, SLICE-R6, COLROM-R6), QC 3, KV 3 (+1 other flow error).
  STALE 17 (S81 only, non-held: cancelled-superseded/failed): COLROM-R6 3, LEAF-R10 5, COL-H9R0-R4 3.
  92 held-with-reason rows no longer STALE; 193 held for plan events.
  Detail lanes/OWNERS-SWEEP.tsv
- 2026-11-23 00:51 PST 00:55 rows 448 (HEAD 0 flagged; S81/QC/KV only). S81: 111 STALE, 1 UNOWNED (dsdv_slice_lepe_nh_mus_C__t1), 3 HELD-LBL. QC: 2 STALE, 1 HELD-LBL. KV: 3 HELD-LBL (kv3_sys_c, kv3_pc_v1 cl*), 2 DEAD-OWNER (kv3_hub_Wi, kv3_hub_C), 6 WAIT-BIND. FAILED-NO-RELAUNCH 0 outside LBL holds. Columns per spec; tool bin/owners_sweep.py + VIS-COVERAGE join.
- 2026-11-23 01:58 PST 01:58 sweep, 449 rows (HEAD 2, KV 48, QC 50, S81 348); tool bin/owners_sweep.py + HELD-EVENT for plan-event holds (D29/V4/r18/J9).
  S81: 1 UNOWNED (dsdv_slice_iq_C__t1), 7 FAILED-NO-RELAUNCH (COL-H9R0-R4 2, COL-H10-R4 1, LEAF-R10 3 s81sl_leaf t29/t44/t71, SLICE-R6 1), 15 STALE>3h cancelled/superseded, 248 HELD-EVENT, 77 OK.
  QC: 2 FAILED-NO-RELAUNCH (CLAND ring band, owner FAIL-ROUTE-1115), 1 DEAD-OWNER (sle_fw_v1__clf58b4dfb, VIS-QC-form_fefw), 27 HELD-EVENT.
  KV: 2 DEAD-OWNER (kv3_hub_Wi FABLE-FIX-KV-HG; kv3_hub_C KV-RINGMAC-R1), 26 HELD-EVENT incl 3 failed rows waiting D29 bind (kv3_pc_v1 cl4ea58a5c/cl23f6a148 FAM-KV-IOPC-R4, kv3_sys_c FAM-KV-HUBC-SYSC-R2).
  HEAD: 2 OK. FABLE-UNC-S81-* lanes not yet posting. Detail lanes/OWNERS-SWEEP.tsv
- 2026-11-23 02:52 PST 02:5x sweep 446 rows: OK 127, HELD-EVENT 304 (S81 249, QC 27, KV 28; plan-event holds), FAILED-NO-RELAUNCH 11 (S81 9, QC 2), STALE>3h 2, UNOWNED 1 (S81 dsdv_slice_iq_C__t1 cancelled), DEAD-OWNER 0 (was 3).
  New vs a6ef39f: FAILED-NO-RELAUNCH S81 col_h9_r0_p2__t1__cl0045af7b + dsdv_slice_c1x_C__t7 (FAM-S81-COL-H9R0-R4 / FAM-S81-SLICE-R6); STALE QC sle_su_l1__cl5ea486db, S81 dsdv_slice_c1x_C__t8; HELD-EVENT +2 KV +1 S81.
  Still failed, not relaunched: S81 leaf t29/t71/t44f6 (OPUS-FIX-S81-LEAF-R10), col_h9_r0_p5 x2, col_h10_r1, lepe_nh_mus; QC slw_st_a_v1 + sle_st_a_v2 CLAND ring band (OWN-QC-1123).
  Cleared since a6ef39f: all 3 DEAD-OWNER, 13 of 15 STALE.
- 2026-11-23 03:52 PST 03:51 sweep, 445 unsigned rows (S81 347, QC 49, KV 51, HEAD 1). Flags: FAILED-NO-RELAUNCH 17 (S81 11, KV 3, QC 3), STALE 140 (S81 131, QC 9), UNOWNED 1 (S81 dsdv_slice_iq_C__t1), DEAD-OWNER 0. KV 11 WAIT-BIND. S81 stale concentrated: LEAF-R10 44, COL-H9R0-R4 21, COLROM-R6 18, SVC-R9 16. File lanes/OWNERS-SWEEP.tsv committed d680a9c
- 2026-11-23 05:53 PST 05:55 sweep, 444 rows (S81 347, KV, QC, HEAD none flagged); new cols successor_lane, successor_alive. Only S81-J9-ASSEMBLY-R6 has posted TAKING (05:51); all other successors pending (no post file yet) so SUCCESSOR-PENDING on 413 mapped rows (S81 337, KV 41, QC 35).
  Flags: S81 STALE 151, FAILED-NO-RELAUNCH 23, UNOWNED 5, DEAD-OWNER 1; QC STALE 12, FAILED-NO-RELAUNCH 5; KV FAILED-NO-RELAUNCH 2, WAIT-BIND 16.
  Unmapped (no successor): S81 dsdv_slice_iq_C__t1, lepe_nh_mus_LP__t1, lepw_mu_C__t1, lepw_mu_LP__t2, lepw_mus_LP__t2 (UNOWNED), lepw_mus_C__t1 (DEAD-OWNER), bk_sel__t2, gunit__t1; QC glue, slw_st_a_v1 cl* variants.
  Biggest stale groups: S81-COL-J9 55, S81-LEAF-J9 55, SVC-J9 16, SLICE-J9 9, MISC-SERDES-J9 8.
  File lanes/OWNERS-SWEEP.tsv committed.
- 2026-11-23 10:53 PST 10:51 sweep: 441 rows (Codex log counted, resumed lanes alive), 331 unflagged. 
  S81: 40 UNOWNED (held col_h10/col_h9 pv variants + svc t2/t4), 3 DEAD-OWNER (svc t1/t3), 31 STALE.
  QC: 6 FAILED-NO-RELAUNCH (glue 15h, sle_st_a_v2 pv4242de79, slw_st_a_v1 x3 CLAND ring band, slw_st_a_v2 hold-CTS), 16 STALE; owners QC-V4/FAM-QC-SLWSLE-R1/CODEX.
  KV: 2 FAILED-NO-RELAUNCH (kv3_pc_v1 cl7f648944/cl4ea58a5c global_place 13h, TAP-GRID-R6/KV-D29), 29 WAIT-BIND. HEAD: no flags.
  Note: hub builder has no successor_lane columns/SUCCESSOR-PENDING (output lacks them); agent_ids.tsv missing.
- 2026-11-23 15:48 PST OWNERS-SWEEP 15:4x: 440 rows (S81 344, QC, KV, HEAD); HBM skipped; Codex posts count as owner activity, pre-11:40 lanes = LIMIT-RESUMED.
  UNOWNED: QC 6 (cbf_q00_s2, cbf_q01, cbf_q01_s2, cbn_q01__cl*), S81 6 (dsdv_slice_lepe_*/lepw_*_LP, s81sl_kv_leaf__t1/t2).
  FAILED-NO-RELAUNCH: QC 6 (glue, slw_st_a_v1__cl*, sle_st_a_v2__pv4242de79; CLAND ring band), KV 2 (kv3_pc_v1__cl4ea58a5c, cl7f648944; global_place).
  STALE >3h: S81 34 (col_h10_r*, serdes__t14, dsdv_slice_iq_C__t1), QC 17 (sle_*, glue); LIMIT-RESUMED QC 3 (OPUS-FIX-QC-V4-R2); HEAD none flagged.
  Table: lanes/OWNERS-SWEEP.tsv
- 2026-11-23 15:53 PST OWNERS-SWEEP 15:5x re-run (440 rows), COORD 16:0x assignments marked ASSIGNED-PENDING-17:00 (KV pc_v1 ASSIGNED-HELD-20:00).
  Assigned: QC cb 6 -> OPUS-FIX-QC-V4-R2, QC glue/st_a/sle 17 -> QC-V4, S81 col_h10 8 -> S81-COL-J9, LP slice/iq_C 2 -> S81-SLICE-J9, serdes t14 1 -> FABLE-OPEN-S81-A, KV pc_v1 2 -> FABLE-OPEN-KV.
  No-post-since-16:00 not evaluable: host clock is 15:5x, all assigned lanes posted 15:42-15:51.
  NEW flag: S81 STALE 23 outside assignments (col_h9_r0_p6, dsdv_slice_c1x_C t1/t5, gunit__t1, serdes__t1__cl*).
  No new UNOWNED, FAILED-NO-RELAUNCH, or DEAD-OWNER rows.
- 2026-11-23 17:24 PST OWNERS-SWEEP 17:2x (440 rows); DEAD-OWNER judged on posts after 17:25.
  S81 UNOWNED 87 (col_h10_r2__t1__cl1f5d6c2a__pv*) -> S81-ALLFIX-COL (last post 17:00, stale).
  S81 STALE 34 (col_h10_r0/r1, serdes__t14, dsdv_slice_iq_C, LP slice); QC STALE 17 (sle_*, glue).
  KV FAILED-NO-RELAUNCH 2 (kv3_pc_v1__cl4ea58a5c, cl7f648944), KV-ALLFIX last post 16:40.
  No DEAD-OWNER rows; S81-ALLFIX-SLICE last post 16:29.
- 2026-11-23 17:50 PST OWNERS-SWEEP 17:5x (440 rows); ALLFIX lanes counted as owners, DEAD-OWNER judged on posts after 17:25.
  UNOWNED 0 (S81 87 col_h10_r2 rows now S81-ALLFIX-COL; all 7 ALLFIX lanes posted 17:27-17:49).
  S81 STALE 34 (col_h10_r0/r1, serdes__t14, dsdv_slice_iq_C) -> ALLFIX-COL/INT/SLICE; many are cancelled/superseded.
  QC STALE 17 (glue, sle_*) -> QC-ALLFIX; KV FAILED-NO-RELAUNCH 3 (kv3_hroot, kv3_pc_v1__cl4ea58a5c, cl7f648944) -> KV-ALLFIX.
  No DEAD-OWNER rows; HEAD clean.
- 2026-11-23 18:51 PST OWNERS-SWEEP 18:5x (440 rows); ALLFIX lanes counted as owners; all 7 posted 18:00-18:50 (COL oldest 18:00); no DEAD-OWNER, no UNOWNED.
  S81 STALE 34 (col_h10_r0/r1, serdes__t14, dsdv_slice_iq_C, LP slice) -> ALLFIX-COL/INT/SLICE; many cancelled or superseded.
  QC STALE 17 (glue, sle_*) -> QC-ALLFIX.
  KV FAILED-NO-RELAUNCH 3 (kv3_hroot, kv3_pc_v1__cl4ea58a5c, cl7f648944) -> KV-ALLFIX; A1b kit_topology rows not separately visible in the table.
  epyc11 (online 17:53): 0 kit-wave rows, load 0.2, no jobs landed yet.
- 2026-11-23 19:50 PST OWNERS-SWEEP 19:5x (134 rows, was 440 at 18:50); ALLFIX rows credited to integrators, split lanes credited via ledger.
  No UNOWNED. DEAD-OWNER 1: dsdv_slice_lepe_mu_LP__t2 (S81-MISC-SERDES-J9). STALE: S81 34 (col_h10_*, S81-COL-J9), QC 18 (sle_*, glue).
  KV FAILED-NO-RELAUNCH 3: kv3_hroot (KV-D29), kv3_pc_v1__cl4ea58a5c/cl7f648944 (KV-ALLFIX).
  Multi-family owners: QC-ALLFIX-COLL 4, FABLE-RC-QC 4, OPUS-FIX-QC-V4-R2 3, QC-V4 3, FLOW-OPS-R3 3, OPUS-FIX-S81-SVC-R9 2 (svc_hi+svc_lo), S81-ALLFIX-INT 2.
  Table: lanes/OWNERS-SWEEP.tsv
- 2026-11-23 20:50 PST OWNERS-SWEEP 20:5x (127 rows, was 134); owners via ledger/ALLFIX tsv; KV-ASTK-TIED, KV-R8-LANELOSS excluded.
  No UNOWNED, no DEAD-OWNER. S81 STALE 35 (col_h10_*, owner S81-COL-J9, no post since before 18:50); QC STALE 1 (tt_ctlm, QC-TTC-RETIME).
  KV FAILED-NO-RELAUNCH 3: kv3_hroot (KV-D29), kv3_pc_v1__cl4ea58a5c/cl7f648944 (KV-ALLFIX).
  Lanes with 3+ unrelated families: FABLE-RC-QC 6, KV-D29 5, OPUS-FIX-QC-V4-R2 3.
  Table: lanes/OWNERS-SWEEP.tsv
- 2026-11-23 21:51 PST OWNERS-SWEEP 21:5x (153 rows, was 127); new lanes credited via ledger.
  No UNOWNED, no DEAD-OWNER, KV FAILED-NO-RELAUNCH cleared (was 3). HEAD clean.
  STALE: S81 35 (col_h10_*, S81-COL-J9, ALLFIX-COL last post 20:34), QC 1 (tt_ctlm, QC-TTC-RETIME).
  Multi-family lanes: PRECHECK-1119 6 (kv3_pc, sle_st, kv3, kv3_hgi, cbn, slw), KV-D29 4, KV-HG-CAP 3, OPUS-FIX-QC-V4-R2 3 (cbn, cbf, sle_st).
  Also 2-family: S81-OPEN-DEMAND (col, dsdv_slice), S81-J9-ASSEMBLY-R6 (serdes, gunit), QC-ALLFIX-COLL.
- 2026-11-23 22:51 PST OWNERS-SWEEP 22:5x (155 rows). UNOWNED 1: HEAD s81hd_lep_pair. No DEAD-OWNER, no KV FAILED-NO-RELAUNCH.
  STALE: S81 35 (col_h10_*, S81-COL-J9, ALLFIX-COL posted 22:40), QC 1 (tt_ctlm, QC-TTC-RETIME).
  KV-OPEN-INCORE: last post 20:20 (DONE i2), 2.5 h silent, owns 0 unsigned rows; handoff exists, treat as finished unless COORD wants more.
  Multi-job lanes: QC-V4 7, PRECHECK-1119 6, PRECHECK-CELLCAP 4, FABLE-RC-ALL 4, KV-HG-CAP 3, KV-D29 3, FLEET-WATCH-1015 3, OPUS-FIX-QC-V4-R2 3.
  EPYC7-DISK has no post file yet.
- 2026-11-23 23:52 PST OWNERS-SWEEP 23:5x (447 rows, 74 live lanes). No UNOWNED, no FAILED-NO-RELAUNCH, HEAD and KV clean.
  DEAD-OWNER 1: S81 eng__t1 (S81-OPEN-ENGCHAN, last post 19:15, silent before the 23:41 limit).
  STALE: S81 36 (31 cancelled-superseded, 5 held for plan event: dsdv_slice_c1x_C t1/t5, c3x_C t1, serdes__t14), QC 2 (glue superseded, tt_ctlm held for plan event).
  No flagged row is without a plan or lane; superseded rows need no action.
  Multi-job lanes: COORD-SNAPSHOT 7, FABLE-RC-ALL 6, PRECHECK-1119 4, QC-CB-PROBE 3, PRECHECK-CELLCAP 3, S81-ALLFIX-SLICE 3.
- 2026-11-24 00:03 PST OWNERS-SWEEP 00:0x (446 rows), watcher/precheck lanes no longer owners, DEAD-OWNER = owning lane silent >2 h even with mentions.
  UNOWNED S81 89 (col_h10_r2 pv*, dsdv_slice_*_C). DEAD-OWNER KV 34 (OPUS-FIX-KV-PV-R7 29, KV-D29 3), S81 17 (FAM-S81-SLICE-R6 13), QC 8 (QC-ALLFIX-COLL).
  STALE S81 35, QC 2. S81-OPEN-DEMAND 22:35, FAM-S81-COL-H9R0-R4 22:53, OPUS-FIX-S81-SVC-R9 23:14 are inside 2 h at 00:02 so not DEAD yet.
  Row jump 153 to 447: S81 rows 52 to 344 (held by die owner), KV 34 to 60; stages file has no history.
- 2026-11-24 01:11 PST OWNERS-SWEEP 01:1x (446 rows); limit gap 00:44-01:05 excused, DEAD-OWNER only if silent before 23:09 and no post since resume.
  UNOWNED 21: S81 18 (dsdv_slice_c1x_C t1/t5, c3x_C t1 ...), QC 3 (cbf_q01, cbf_q01_s2, sle_st_b_v2__clfde1249e).
  DEAD-OWNER S81 161 (S81-OPEN-DEMAND 99 last 22:35, FAM-S81-COL-H9R0-R4 60 last 22:53), KV 35 (OPUS-FIX-KV-PV-R7 29 last 20:58, KV-D29 4), QC 1.
  STALE S81 35, QC 2. No FAILED-NO-RELAUNCH, HEAD clean.
  Silent before the limit, so not a limit casualty.
- 2026-11-24 01:51 PST OWNERS-SWEEP 01:5x (446 rows). UNOWNED S81 9 (dsdv_slice_c3x_C t1, lepe_nh_mus_C t1, lepw_mus_C t1 ...). No FAILED-NO-RELAUNCH, HEAD clean.
  DEAD-OWNER (no post since 23:50): S81 62 (S81-OPEN-DEMAND 44 last 22:35, OPUS-FIX-S81-SVC-R9 16 last 23:14), KV 32 (OPUS-FIX-KV-PV-R7 29 last 20:58), QC 1.
  Silent since before the 00:44 limit, none resumed. STALE S81 35 (mostly superseded), QC 2 (tt_ctlm, glue).
  New lanes S81-VPW-CONE, TAPKEY-SITE, KW-REPICK-PIN, HEAD-WEST posted 01:37-01:47 but own 0 unsigned rows; QC-DEPTH5 owns 1.
- 2026-11-24 02:51 PST OWNERS-SWEEP 02:5x (446 rows). UNOWNED S81 2 (dsdv_slice_lepe_nh_mus_LP__t1, lepw_mus_LP__t2, held for RIP). No FAILED-NO-RELAUNCH, HEAD clean.
  DEAD-OWNER (no post since 00:50): S81 66 (S81-OPEN-DEMAND 42 last 22:35, OPUS-FIX-S81-SVC-R9 16 last 23:14, S81-OPEN-FSTART 8 last 23:58), KV 30 (OPUS-FIX-KV-PV-R7 29 last 20:58, KV-HUB-HOLD 1).
  STALE S81 35 (mostly superseded), QC 2 (tt_ctlm, glue). QC glue now owned by QC-INHOLD-BUDGET (cancelled-superseded). sle_st_b_v2__clfde1249e owned by QC-ALLFIX (placed, route held).
  QC rc99/rc101 are PROBE-PENDING in ALLFIX-QC.tsv (not launched). New lanes KV-SPINE-REWIRE 02:48, ROMW-LOSS-1124 02:37 posting; RSTSOLVE has no post file.
- 2026-11-24 03:50 PST OWNERS-SWEEP 03:5x (446 rows); FABLE-*, HOURLY-* now excluded as owners in owners_sweep.py (backup .bak-1123).
  UNOWNED S81 2 (dsdv_slice_lepe_nh_mus_LP__t1, lepw_mus_LP__t2). No FAILED-NO-RELAUNCH. HEAD clean.
  DEAD-OWNER (no post since 01:50): FAM-S81-COL-H9R0-R4 60 (last 01:19), OPUS-FIX-S81-SVC-R9 16 (23:14), S81-OPEN-FSTART 2, KIT-FWDCLK-SDC 1, WATCHDOG-SWEEP 1.
  STALE S81 35 (mostly superseded), QC 2 (tt_ctlm, glue).
  col_h10_r2 12 rows: S81-ALLFIX-INT 10 + SEAT-MATCH-AUDIT 2, both posted 03:13-03:49; not RSTSOLVE.
- 2026-11-24 04:54 PST OWNERS-SWEEP 04:5x (446 rows); reassignments applied, all new lanes posted 03:53-04:50. S81 UNOWNED 0, DEAD-OWNER 0, FAILED 0, HEAD clean.
  21 rows WAITING-GATE (C8: col_h10_r2, svc, LP, serdes), not STALE. S81 STALE 14 remain (col_h10_r0/r1 under ALLFIX-INT/B1-RTHOPS).
  KV DEAD-OWNER 22: KV-OWN-PV 21 (kv3_pv_*, last post 02:34), KV-HUB-HOLD 1 (kv3_hub_Eo, 22:55).
  QC STALE 2: glue (QC-ALLFIX, superseded), tt_ctlm (FLOW-OPS-R3).
  Nothing else flagged.
- 2026-11-24 07:55 PST SWEEP 07:5x PST [OWNERS-SWEEP -> COORD] lanes/OWNERS-SWEEP.tsv (446 rows; new cols fresh_owner, owner_lane_states, sweep_flags). Flagged rows now mapped to fresh lanes: col_h10 x10 -> S81-ALLFIX-INT+S81-C9-ROWS (S81-ALLFIX-COL dead 04:56), s81sl_kv_leaf x3 -> S81-KVLEAF-T2-ARCH (SLICE-C-OWN dead), cbf_q01/_s2 UNOWNED -> QC-CB-SPREAD-R2, KV hub_Eo/pve/hub_C (owners dead 04:55-04:57) -> KV-ALLFIX. No FAILED-NO-RELAUNCH. GAPS no fresh lane covers: (1) 71 S81 s81sl_leaf rows UNOWNED (S81-OWN-LEAF/OWN-MISC dead since 05:11/04:55; KVLEAF-T2-ARCH takes kv_leaf only), (2) QC glue/tt_ctlm STALE (QC-GLUE-IMAGES/QC-ALLFIX have not posted rows yet), (3) 11 unsigned types with no kit-wave row (S81 2, QC 7, KV 2), (4) 119 S81 CBC-FALLBACK rows rely on CBC-RULES-1119 only. 43 superseded-cancelled svc_*/gunit/dsdv rows flagged STALE are noise. Next sweep 08:55.
- 2026-11-24 08:51 PST SWEEP 08:5x PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv 388 rows, fresh list now incl OWN-LEAF/SVC-TIED/LEPW-CHAN/IQF-RELAY/TILE-RESIGN/KV-INCORE-R2/SENDER-SKEW/PV-CAP. Real flags 42, all mapped: S81 DEAD-OWNER 10 col_h10_r0_p1/r1 -> ALLFIX-INT+C9-ROWS; S81 UNOWNED 20 (col_h10_r2 x12, kv_leaf x3, lepw LP x2, kv512, eng) -> mapped; S81 STALE 4 (c1x x2, c3x, serdes). QC UNOWNED cbf_q01/_s2 -> CB-SPREAD-R2; QC STALE tt_ctlm. No FAILED-NO-RELAUNCH. s81sl_leaf and svc gaps now covered. NEW GAP: KV has 84 unsigned types and 0 kit-wave rows (table fell 60 -> 1 row), so no KV owner row can be checked; HEAD shows 2 rows. Next sweep 09:5x.
- 2026-11-24 09:51 PST OWNERS-SWEEP 11-24 09:55 PST: 388 unsigned rows S81/HEAD/QC/KV (HBM parked), lanes/OWNERS-SWEEP.tsv.
  S81 344 rows (292 held for c8/c9 = HELD-OK); 19 UNOWNED + 9 DEAD-OWNER dsdv/s81sl_kv_leaf rows re-mapped to S81-OWN-DSDV/S81-OWN-LEAF (live); 48 STALE = cancelled-superseded (>3h).
  QC 41 rows: 1 STALE (glue, QC-GLUE-IMAGES); sle_st_b_v2 relaunched under HOLD-PAD-FLOW. KV 3 rows: kv3_pv_pair WAIT-BIND; 81 types have no kit-wave row (KV-OWN-PV-R2/HUB-R2 live).
  DEAD-OWNER lanes (silent >2h): S81-FWDCLK-WHATIF (04:06), LANEAGE-SWEEP (07:44), S81-KVLEAF-T2-ARCH-R2 (07:38). 119 S81 CBC-FALLBACK rows held, owners live.
  No FAILED-NORELAUNCH rows.
- 2026-11-24 10:51 PST SWEEP 10:5x PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv 394 rows + KV private kits from private_specs (109 kits, 84 under KV-ALLFIX); commit 74eb04de. KV: 50 FAILED-NO-RELAUNCH (pc 21, hg/hgi 9, pv 5, hub 4, qkd 6, other 5; latest kit FAIL, none live, under 48 h) mapped to KV-OWN-HG-R2/PV-R2/HUB-R2 or KV-ALLFIX; 15 STALE. S81: UNOWNED 10 (kv_leaf 4, LEPW/LEPE LP 4, c3x 1, lepe_mu_C 1), DEAD-OWNER 1 (kv_leaf; KV-D29 dead), STALE 4. QC: UNOWNED slw_su_c x2, STALE tt_ctlm. All map to a live lane, no GAP. Next sweep 11:5x.
- 2026-11-24 11:05 PST SWEEP 11:0x PST [OWNERS-SWEEP -> COORD] owners_sweep.py now skips every kit_wave dies/*/private_retired_specs_* spec (commit 2a84c411; backup .bak-retired-1124); KV private-kit scan skips them too (109 -> 94 kits). 8 KV-ALLFIX running rows (hub_C/Wi/Wo, pv_v12e/v3ne/v5ne/v8/v8e) now read as running from live units (place units or allfix-A5t3-<item> services), not flagged; hg/hgi/io-cor/pv-v1 units also count live. Sweep table pushed a8e2b3e3. Next sweep 12:0x.
- 2026-11-24 11:06 PST SWEEP 11:0x PST [OWNERS-SWEEP -> COORD] S81 re-mapped (commit 222f845e): UNOWNED 0, DEAD-OWNER 1 (s81sl_kv_leaf t1, held, old owner KVLEAF-T2-ARCH-R2 dead 07:11, live S81-KVLEAF-T2-ARCH), STALE 1 (gunit t1 cancelled, no named launcher). 19 held c8/c9 rows tagged HELD-GATE, 47 cancelled rows CANCEL-LAUNCHER, 19 mapped to named lanes (C9-ROWS, OWN-COLH10, OWN-LEAF, OWN-DSDV, LEPW-CHAN, IQF-RELAY, SVC-TIED, SERDES-TAPSKEW, FAM-H9R0, ALLFIX-INT). Still flagged: gunit t1 only; CBC-FALLBACK 119 unchanged.
- 2026-11-24 11:51 PST SWEEP 11:5x PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv 394 rows pushed ca3f8201. S81: UNOWNED 0, DEAD-OWNER 1 (kv_leaf t1 held, live owner KVLEAF-T2-ARCH), STALE 1 (gunit t1 cancelled, no launcher); 37 HELD-GATE, 47 CANCEL-LAUNCHER. The 13 c8 kit-rtl FAILs are not rows in the kit-wave table or private_specs result.json, so no HELD-C8-RECEIPT tag applied (S81-ALLFIX-INT to list them). QC: STALE tt_ctlm (held), slw_fe_v2 (relaunched private kit QC-ALLFIX); cb types held, not flagged. KV: 45 FAILED-NO-RELAUNCH private kits (pc 23, hg/hgi 8, qkd 5, pv 4, other 5) mapped to KV-OWN-*-R2/KV-ALLFIX; 36 running. HEAD clean. Next sweep 12:5x.
- 2026-11-24 12:51 PST SWEEP 12:5x PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv pushed 3b3e4022 (agent_ids current, new lanes QC-SLECTL-PILE/KV-PV-FANOUT/FABLE-FLOW-REVIEW-1255 known). Tagged not flagged: S81 HELD-C8S-STREAM 20 (owner S81-ALLFIX-INT), QC HELD-C1K 23 (QC-ALLFIX), S81 CANCEL-LAUNCHER 47; KV retired specs skipped. Flagged: S81 STALE gunit t1 (no launcher), DEAD-OWNER kv_leaf t1 (live owner KVLEAF-T2-ARCH); QC STALE glue (cancelled), slw_fe_v2 (relaunched); KV FAILED-NO-RELAUNCH 13 (pv 6, pc/phy/hg/hroot/io_cor/sys 7), STALE 6 (3 are SIGNED kits, not real). HEAD clean, no UNOWNED. Next sweep ~14:00.
- 2026-11-24 13:50 PST SWEEP 13:5x PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv 471 rows pushed 67c90c96 (KV now 83 kit-wave rows after A5t5, so private-kit rows no longer needed). S81: only STALE gunit t1 (cancelled, no launcher); 20 c8 types HELD-C8S-STREAM, 47 CANCEL-LAUNCHER, no UNOWNED/DEAD-OWNER. QC: STALE glue (cancelled), native59 + tt_ctlm (held, QC-ALLFIX), slw_fe_v2 (relaunched); 14 HELD-C1K. KV: no tool flags, 2 rows owner silent since the 05:48 limit but covered by KV-ALLFIX. HEAD clean. Next sweep ~14:50.
- 2026-11-24 14:51 PST SWEEP 14:5x PST [OWNERS-SWEEP -> COORD] 14:50 table 73b023c9, 471 rows. S81 29 DEAD-OWNER rows = all col_h9_r0_p4/p5/p6 pv rows (held, not HELD-C8S-tagged) with owner FAM-S81-COL-H9R0-R4, which is only the LANE-STATUS filing name of the live FAM-S81-COL-H9R0 (last post 11:36, runitem col_h9_r0_p2 unit active): false flag, now aliased (fbb72bb8). Slow posters S81-OWN-LEAF, KIT-FWDCLK-SDC, S81-OWN-COLH10 no longer read dead. Still flagged: S81 STALE gunit t1; QC STALE glue, native59, tt_ctlm, slw_fe_v2; 14 HELD-C1K, 93 HELD-C8S-STREAM. KV, HEAD clean. Next sweep ~15:50.
- 2026-11-24 15:49 PST SWEEP 15:49 PST [OWNERS-SWEEP -> COORD] OWNERS-SWEEP.tsv 475 rows pushed. S81: STALE 1 (gunit) HEAD: clean QC: STALE 4 (glue,native59,slw_fe_v2) KV: FAILED-NO-RELAUNCH 6 (kv3_hg_v1,kv3_hg_v1p2,kv3_hg_v1p3) Tagged not flagged: HELD-C1K 14, CANCEL-LAUNCHER 47, HELD-C8S-STREAM 92 Hourly at :48; owners per COORD 15:5x (kv3_hg_v1 KV-OWN-HG-R2, kv3_pc KV-OWN-RSTREACH, kv3_hub_Wi KV-OWN-HUB-R2).
