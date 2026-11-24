# KV-INCORE-R2 handoff (Opus 5.5, started 11-23 22:55 PST). Successor to KV-OPEN-INCORE. ONE JOB: census item (e), the 23 in-core stations STREETSTN leaves.
States per item: IN-BASE (A5 measurement) / ROW-REBASED (row on A5 + PRE + scoped strict bind) / ROW-DROP (reason). First list due 00:30 PST.
## Dirs (epyc10 /srv/opentallas-scratch2/claude/kv-incore-r2 = W)
- W/rows/ROWS_KV-OPEN-INCORE.py 62c2c39b7a5a (predecessor row, with LAT pass). W/incore_list.py PLAN OUT = STREETSTN-definition in-core list.
- W/d1.sh: dry run on KV-ALLFIX A5 s9 (STREETSTN output, c74876e2fab1) -> list -> row -> list.
- W/compose_r2.sh = KV-ALLFIX grow/compose_grow_rt.sh with O=W/TAG; W/b1.list = a5.list + my row after STREETSTN (before ISTPRICE/LATREGEN).
- KV-ALLFIX A5: epyc10 /srv/opentallas-scratch2/claude/kv-allfix/grow/A5 (run_a5.sh, a5.list).
## Predecessor result: I2 (A2g + row) PRE PASS, strict GEOM-STATION-IN-CORE 0, die in-core 0, pin hops>405 0; +1 stn hgi_v3 ft8/16/17/18/20, hgi_v4 ft16.
## Log
- 22:55 TAKING. 23:0x d1 dry run launched (ot-run epyc10).
- 23:06 d1 (row 62c2c) on A5 s9: 23 -> 5 left (pv_v3e ft4/5/14/15/16, x 684.104 = 0.6 um off core_box, inside STREETSTN 1-um tol). d2 = W/rows/ROWS_KV-INCORE-R2.py 67e32f55dcee (TOL 1.0): 23 -> 0. +1 stn hgi_v3 ft8/16/17/18/20, hgi_v4 ft16; L346 90->97, L341/342/343/1431 +1.
- 23:1x B1 (W/b1.sh, list W/b1.list = A5 s9 + row + A5 steps 10-18, rt 780ae119cdc4) waits A5 DONE then composes + census; G1 (W/g1.sh) waits B1 then PRECHECK + elab + scoped strict bind (5 types) + LATCHECK. Logs W/b1.otrun.log, W/g1.otrun.log.
- 23:22 MILESTONE 1 posted: all 23 ROW-REBASED. B1 plan c644daff4f26 (W/B1/plan.json): in-core 0, strict GEOM 0, G0 in-core 0, pin hops>405 0; PRE = A5's 27 FAILs (W/prediff.py: 0 new/worse). LAT L346 90->97, L341/342/343/1431 +1. G1 cancelled (wrong PRE condition); G1b (W/g1b.sh, log W/g1b.otrun.log, out W/G1b) = PRECHECK + elab + scoped strict bind 5 types + LATCHECK running.
- 23:52 CORRECTION posted: row changes 16 types (not 5), moves 55 internal stations (0 count change); no bind had run (G1b/G1c refused by PRE); B1 was on the epyc10 grow/tree (not private).
- 23:58 SIBLING ANSWER posted: landing groups sys_c->kvs_attn (+2 predicted: 95->97) and hub_C->dcal (+1); LATCHECK decides.
- C1 = A5r 41044638cda3 (epyc11 kv-allfix/grow/A5fix/f1w.json) + row; epyc11 W/tree = ot-tree-fork (W/fork.otrun.log, unit oth-ubuntu-4112864-1795506747); then W/c1.sh -> W/gate_r2.sh (OT_PLAN_GATE_PRE=warn ONLY behind guard classes==RSTREACH, COORD ruling per KV-ALLFIX 23:30). Out W/C1, W/gate_C1.
- 00:2x C1 dropped (moves the fixed pair image). C2 = row 67e32f55dcee + ROWS_KV-INCORE-R2-NOSEAM f8001a956bcb (io_cor_v1 ft4 6->4, ft15 5->4). COORD: epyc10/epyc9 only, base A5s (A5r minus FTLOCKUP minus STREETSTN). P1 evidence withdrawn (tainted sidecar).
- epyc10 W/tree = fork of epyc11 grow/tree (W/fork10.otrun.log). When A5s done: copy A5s plan.json/asbuilt_allfix_A5s.json/eW_sidecar_A5s.json from epyc11 into W/in, run W/c2prep.sh (ot-run), POST expected table, then W/gate_c2.sh (KV-ALLFIX gate_grow_a5s.sh with own paths; pad tables unchanged, derives R8 main only).
- Owed: regen_constants full (param_regen + src-root) C2 vs A5s bind; KV-SENDER-SKEW answer on ft4/ft15; bus-list single-user proof; zero-slack L346/L353 line in A6 ledger.
