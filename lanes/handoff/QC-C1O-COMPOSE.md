# QC-C1O-COMPOSE handoff (updated 2026-11-25 01:01 PST)
Lane: stage + compose QC C1o (child of QC-ALLFIX). Dirs: intel1 + epyc10 /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE (epyc10 mirror, no tree).
Base: C1n-r2 a372ae84fa2a (C1n 26036a + RRDRV-REMAP ebb40d + RRDRV-FAR 4eb637), sidecar 0391a5add8e7. Cut 03:00 PST; later -> C1p.
Current candidate: C1o v3 4c5b5a9bb1f7 (c1o_v3/plan_c1o.json) = r2 + CB-PIPEREACH + DEMACRO-QC-C1o f143e6d8 + STA-RELAY-PRUNE 960d3bc4 + COLL-IRN-SEAT 3872208e + KVQC de-stack 7 types (glue + 6 sc; sle_su_c/cbf_q00_s2/cbf_q01_s2 excluded: FTSITE/BITSITE).
Gate v3: guard PASS 0 silent (3676 intended), SIDECAR 0, rreval 0 (nt/c1n_* only!), far census 0, FTSITE 3/3, BITSITE 1403 (+422 DEMACRO intra-station, flagged to SITE-IN-MACRO), ledger key check PASS.
PRE: intel1 tree/ (fork of epyc11 QC-CB-C1L/m/tree + C1n overlays ov/), mkO.sh, rt 689a2622f6a4 (has 899f9018, e4ffa951, a0ddbaeb), --crit --priority die; log mkO_v3.log, pre_c1o_v3.log. COORD: no bind before PRE PASS.
Pending rows: SUL1-FACE-BAND (ROW-STAGED, intel1 QC-SUL1-BAND/out, overlay sink_bins/c1o_sul1 x2), STA-BTLAT3/BTSEAT, HALOCORNER-ROW (02:45), GLUE-CLUSTER (draft), CORE-TAP-EARLY-STA (gateCT2 running; covers st_a only, not coll_core).
To C1p: FWLEAF-1 (probe LBL-refused; relaunch with OT_PROBE_THROUGH=1 at 01:15 if no ack), STB-SPLIT.
Scripts: c1o_build.sh NAME STEPS GROWS kvqc KVQC_TYPES PRUNE_ROWS (never edit while running); c1o_rows.py steps pipereach/fwleaf/coretap/jsonpatch/prune/seatset; ledger_pre.sh PLAN SPEC; bitsite_diff.py.
