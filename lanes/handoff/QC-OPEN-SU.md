# QC-OPEN-SU handoff (11-23 19:3x PST)
Parent QC-ALLFIX / QC-ALLFIX-SU. Job: per-row state for rc105 su_c, RED +2, rc103 su_l1, SUC-Q0, rc99, rc101.
DONE 19:32: all 6 IN-COMPOSE C1b 62ce8aba0292 (epyc7 /srv/opentallas-scratch2/claude/QC-ALLFIX/rows_c/plan_c1_fix1.json),
evidence = plan diff vs C4 81fd3e6370c0 (kw45/snap_qwen_compute/qwen_compute_v4c4 plan_of_record); ALLFIX-QC.tsv rows updated; post 7ffe38a1.
Scripts: localhost scratchpad qcopensu/verify.py, verify2.py.
Open risk (told QC-ALLFIX): RED2 is a tree-file row (zz_extra_red_plus2_c4.json 3daaf93866cb + asbuilt land_r8_extra);
the epyc11 cD fork comes from the C4 snap, so ov_red2 (+ov_r8) must be overlaid before the C1b strict. cD fork waits on tree-copy slots.
No units launched or adopted. Next if asked: su_c/stm/sc probes on C1b after its strict (~21:45).

## Job 2 (COORD 19:4x): C1x probes, probe-only (FIX3 = QC-ALLFIX-SU)
- 21:50 launched 6 stm/sc reps on C1-noSU 12b66c0e4829 (strict 0, LAT 1922): epyc7 QC-ALLFIX/cC/{tree,bind}, rt 70b6f0430ea9 + OT_TOOLSTALE_RT (9b19260 refused: reset gen differs from bind), gen epyc7 (epyc11 lacks plan). Units intel2 systemd runitem-<item>; specs ~/coord/autopilot/private_specs/QC-OPEN-SU/. Script intel2 /srv/opentallas-scratch2/claude/QC-OPEN-SU/probe.sh (env RT, PROBE_HOST).
- Pre-SU2R stm/sc form. TODO: su_c x3 + stm/sc rerun on C1c+FIX3 bind (cE) when QC-ALLFIX posts strict PASS.
- Reads: place, CTS post-hook, final 5_1_grt.odb, full-cause census -> post to QC-ALLFIX + FABLE-RC-QC.
- 23:48 CORRECTION e37bd8b9: 23:04-23:31 place posts mixed min (hold) paths into setup; x_ctl_o q[85] test case WITHDRAWN. ALWAYS read by Path Type (scratchpad qcopensu/rpt.py). Rpts show worst per group only.
- C1b/C1c/C1d/C1e strict failed or cancelled; epyc11 c1d/tree holds cancelled plan c2856018af83 (refresh before use).
- 00:41 11-24 STATE: 6/6 C1-noSU probes past CTS (final reads posted 885bad56, 00:34, c0e3d3b3); all in GRT. c0e3d3b3 also CORRECTS 885bad56/776be839: tapsrc difference mixes early/late source latency (~22 ps on one tap) with tap offset. NEXT: GRT (5_1_grt.odb) full-cause census per probe.
- C1g 96cce77c1e2f strict: epyc7 QC-ALLFIX/cF, log bindC1g.ot, in R8 re-bind loop 00:41. Only on strict 0 + LATCHECK PASS launch 9 probes (3 su_c + 6 stm/sc), label PROBE; check cF/bind/bind_tool.json vs rt c66090747375 first. FAIL -> launch nothing, report.
- HOST: no COORD answer yet. epyc11 is out (COORD 1502, 00:16). Default epyc7 from cF, no copy, ot-run admission decides; fallback epyc2 via copy class AFTER the pass. No copies outside ot-run; obey refusals.
- epyc11 QC-OPEN-SU/c1d (57 GB) stale, do not use. sc far-reset = QC-SC-FARRST.
- 01:25 11-24: C1g PASSED (9a790101). 9 PROBE kits launched 01:20-01:23 from epyc7 cF, rt c66090747375 (gen shas match), specs private_specs/QC-OPEN-SU/*_11240* (units runitem-<item> or -<pid> suffix where old item units still run). Posted e1ae0337: place ~03:00, CTS ~04:00, GRT census ~05:00; C1-noSU GRT census ~02:00. Waiter script scratchpad qcopensu/scan.sh keyed by spec dir. C1g hang check ALIVE (7281c520). epyc11 c1d DELETED via ot-delete.
- 02:10 11-24: 3/3 C1g su_c probes FAIL gen (cws1 stage-0 FT sites snap to one site; plan issue, 6957a3f9); 6 C1g stm/sc probes in gen_lint+. C1-noSU GRT census done: sle_stm_v3 (607ea79d: ovfl 0, TT setup -4.7, int hold MET, only port hold -137) and sle_sc_v3 (7e7c6971: TT setup -241.8 reset-monitor t69 REACH class, int hold MET, port hold -129). QC-SC-FARRST stood down -> QC-ALLFIX. GRT STA method: epyc7 /srv/opentallas-scratch2/claude/QC-OPEN-SU/sta/grtsta.{tcl,sh} via ot-run; runner scratchpad qcopensu/grtrun.sh x <item>; grp.py groups. Remaining GRT: sle_sc_v1, sle_stm_v1, slw_sc_v2, slw_stm_v2.
- 04:20 11-24: Scripts are in scratchpad qcopensu/ (scan.sh runs on intel2 via ssh bash -s; wait.sh; grtrun.sh = C1-noSU GRT census; ctsrun.sh DES KITSTAMP 4_cts = C1g CTS census; sta tcl in epyc7 QC-OPEN-SU/sta). Sign-off path, all in detail route on epyc7 (no resume needed): sle_stm_v3, sle_sc_v1, slw_sc_v2, and since 03:56 sle_stm_v1__cl27746664 + slw_stm_v2__cl1ca9c415 (GRT gates met, 7bbee8e5). Verdict ETA 07:30-09:30.
- SC3-MONLEG: full strict + LATCHECK runs on epyc9 as QC-OPEN-SU/sc3/sc3full.ot (PRE_RC 0, ELAB_OK). Afterwards post ROW-REBASED and run a CTS probe of sle_sc_v3 from that bind.
- Next bind in the epyc9 fork: overlay row/plan_c1g_sc3_col_sul.json (bf43ae13d859 = SC3 + COLSYNC + SULANE-UNSIGNED), PRE, then scoped strict --types sle_su_c,slw_su_c__cl19bb38ef,slw_su_c__cl92142dac,slw_su_l1__cla2a78701,sle_su_l1__clc6d66f5b,sle_su_l0__cl086d85ba,slw_su_l0__cl1e5219ea,slw_su_l0__cl76fb247e. C1h plan: plan_c1h_sc3_col_sul.json e10a0222b2a8. GENDRY D census is in d1caffe5.
- x_ctl class: slw_sc_v2 C1g CTS +84.22, no row (29c89876). sle_sc_v1 C1g CTS census running (hook before-repair wns +97.31); post the side-by-side.
