# QC-C1O-COMPOSE handoff (updated 2026-11-25 01:44 PST)
Lane: stage + compose QC C1o (child of QC-ALLFIX). Dirs: intel1 + epyc10 /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE (epyc10 mirror, no tree).
Base now: C1n-r2 a372ae84fa2a, sidecar 0391a5add8e7. FINAL base must be C1n-r3 (QC-CB-C1L rows CA-REDERIVE + RESETPUB-SCV3: sidecar count_aligned stages 2 vs plan tx/rx stages -> CLOCK_LANDING; slw_sc_v3 collector_tree not republished -> RESETPUB FAIL). Cut 03:00 PST; later -> C1p.
Order (QC-ALLFIX/COORD): rows -> SINKBINS (lane QC-SINKBINS, 51 types, ROW-READY ~02:45, retaps + reset-tree republish) -> CA-REDERIVE LAST -> PRE -> bind.
Candidate (NON-FINAL, on r2): C1o v7 a261ac317ad2 (c1o_v7/plan_c1o.json), sidecar 2379a9fe62e7 (rows/halo/sidecar_hc3.json) = r2 + CB-PIPEREACH + DEMACRO v2 731e98d91d28 + STA-RELAY-PRUNE 960d3bc4 + COLL-IRN-SEAT 3872208e + HALOCORNER 87eb8e0a4396 + DESTACK v2 8562a9cc93cf (7 types; sle_su_c FTSITE, cbf_q00_s2/q01_s2 +19 BITSITE excluded).
Gate v7: guard PASS 0 silent (3676 intended), SIDECAR PASS 0, rreval 0, far 0, FTSITE 3/3, BITSITE 981 (=C1n), ROW-LEDGER PASS (spec_v7.tsv).
PRE: by path on read-only launch tree intel1 .../QC-C1O-COMPOSE/launch_689a2622f6a4 (rt 689a: 899f+e4ff+a0dd) via preP.sh NAME PLAN SC; logs preP_v7.log / pre_c1o_v7.log. Shared tree .../QC-C1O-COMPOSE/tree is READ-ONLY for row lanes until 03:00 (no forks; intel1 disk).
Pending rows: SUL1-FACE-BAND (tree files sink_bins/c1o_sul1 x2), STA-BTLAT3 (masters signed, PRE running), GLUE-CLUSTER (needs rt after bae0396747), CORE-TAP-EARLY-STA (st_a only), SINKBINS, CA-REDERIVE.
To C1p: FWLEAF-1 (relaunched 01:18 with OT_PROBE_THROUGH=1, spec private_specs/QC-FWV1-HOLD/qwen_compute_sle_fw_v1__cl9d029624_1125011806, run-item on intel2), STB-SPLIT.
Scripts: c1o_build4.sh NAME STEPS GROWS kvqc TYPES PRUNE NEW_SC SC_ROWS KVQC_SCRIPT BASE SC POST_CMD (POST_CMD = CA-REDERIVE: args plan_in sc_in plan_out sc_out); c1o_rows.py; ledger_pre.sh PLAN SPEC; preP.sh.
