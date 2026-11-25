# QC-C1O-COMPOSE handoff (updated 2026-11-25 00:19 PST)
Lane: stage + compose QC C1o (child of QC-ALLFIX). Work dir intel1 /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE.
Base: C1n 26036a30b94f + sidecar 0391a5add8e7 (copies in base/). QC-ALLFIX 00:2x: final base = C1n-r (QC-CB-C1L: C1n + QC-RRDRV-FIX rr_tN remap); cut 03:00 PST, later rows -> C1p.
Guard: rt ebc6556ec3d0 compose_drop_guard bca33ce (has b62de070 + 6009f0ed). OT_COMPOSE_DROP=fail.
Rows:
1 CB-PIPEREACH (QC-CB-PIPESEAT) plan 0f77be78cc8d on SPREAD 002c58551eec; row rows/pipereach/x/reach_r2 (tgz 9ac4b9b73c75). C1n pipe keys == 002c on 17/17 types (base consistent). C1o-pre = pre/plan_c1o_pre.json b68ecbabaf17 (338106 keys, 516 stale dropped, all cbf_q00_s2 u_d6 r[5][*], row-intended). Guard rerun with fnmatch-escaped drop list pre/drops_pre_esc.txt.
2 FWLEAF-1 (QC-FWV1-HOLD) row 739975265b88: probe 23:22 was LBL-refused, never ran. Needs relaunch with OT_PROBE_THROUGH=1.
3 STB-SPLIT (QC-STB-SPLIT) on 44a145a65013: retap runM died 23:43 (reset_anchor AnchorError). No row.
4 CORE-TAP-EARLY-STA (QC-STA-CLK) 11d9f716355b on 88374495efff: gate gateCT on intel1 running.
5 KVQC de-stack script 9a853b931a8b (rows/kvqc): rerun on the composed plan.
6 rr_tN: QC-RRDRV-FIX row -> C1n-r base. rreval.py (epyc2 scratch3 QC-RRDRV-CHK) in the gate, 0 bad stages.
Added by COORD: SUL1-FACE-BAND (QC-SUL1-BAND), st_a btab seats + BT_LAT3 (QC-STA-BTLAT3), PG-EDGE-HALO cland (ask QC-STA-CLK), owner-lane fix rows (QC-STA-HOLD, QC-SC-CLAND, QC-COLL-CORE, QC-GLUE, QC-FWV2-BAY, QC-PHY-GEN).
Scripts: c1o_pre.py, c1o_rows.py (pipereach/fwleaf/coretap per type, OVERLAP report), ledger_keycheck.py (ROW-LEDGER key gate), guard_pre.sh.
Tree: fork of epyc11 QC-CB-C1L/m/tree -> intel1 tree/ (fork.log), then C1n overlays as n/mkN.sh (ov_tapbins2, m/hold_c1n, ov_rc97, r8seed) + C1o plan/sidecar.
