# CLEAN-AGGR-R2 handoff (2026-11-21 ~20:3x PST), stood down near the context limit

Scratch: <scratch2>/claude/clean-aggr-r2/tmp on intel2/epyc2/the hosts. Lane clone: epyc8 /srv/opentallas-scratch2/claude/clean-aggr-r2/w (has pytest). The epyc7 clone has no pytest.
Cached AGIdock INDEX: intel2 /srv/opentallas-scratch2/claude/clean-aggr-1121/tmp/agi_index_r2.tsv (do not re-read with the agidock key, per the rules).

## Done
- Damage audit posted (coord af24d0b9c9). Lost SIGNED DB not exported: QC sle_st_b_v2__cl14c98df5__pv41c959f3 (c7ce90ba4af9). slw_st_b_v1__cl6357f1cc__pv6ace3e48 (2033cb1c084a) is also lost, but an older-plan export of it exists. 9 LOCAL_PASS deleted (elements archived). Lane dirs: no lost git work. D27d3 rc143: KV-PLAN-R6 killed it itself.
- main a67ae35f4d: guard closed_unit_refusal (export list + hold_ids.txt) + LOCAL_PASS = signed in attempt_signed. auto_export drain writes and pushes ~/.local/state/ot-delete-guard/exported_records.txt. Until rt/current has a67ae35f4d and one drain has run, every signed closed unit is refused (fail closed, intended).
- 162 exported closed units deleted 19:47 (intel2 +165 GB, epyc7 +110, epyc8 +94, epyc9 +80, epyc10 +64, intel1 +57).
- Canary keep rule re-applied on intel2 (18 runs; log clean-aggr-r2/tmp/canary_del.log).
- Asked TAP-GRID-R5 (66 GB) and mq1 (63 GB) to trim; asked S81-DIE-R5 about epyc2 s81-die-r3-e8 (65 GB; 355 unexported view signoffs).
- Queued on intel2: auto_export drain --scan with 240 h window behind the service lock (log clean-aggr-r2/tmp/export240.log). It exports kv3_phy/kv3_sys_SD_v1, whose sources are still on epyc2 kw43-wave-1109.
- Hourly ot-autoclean: intel1/intel2/epyc2 passes finished. epyc7's first pass failed on a docker inspect timeout (rerun was running). epyc8/9/10 were in apply at 03:4xZ. VERIFY.
- rt/current = 5aab47bd4b12 on all 7 hosts (contains 2095d6a53d).

## Left
- epyc2 scratch2 at 377 GB (target 450). The guard protected 4 of 6 idle dirs. Next: s81-die-r3-e8 after S81-DIE-R5 answers. tools-converge and die-qc-103 hold unexported signoffs, so keep them.
- 40%-free target: epyc7 9%, epyc8 13%, epyc9 17%, epyc10 18%, intel2 22% free on scratch2.
- candMISC5 (epyc7 fam-s81-misc-r4/trees): protected because the hub live-process scan sees the running intel2 run-item PID 3087357 (spec FAM-S81-MISC-R4 t5_1121194641, --hosts localhost) name the same path. The list is host-agnostic on purpose, since hub run-items drive remote jobs. ot-delete it once that run-item ends. An allow_exact line on epyc7 expires ~22:0x and does not help (ancestor-only).
- hold_ids.txt is empty on all hosts. FLOW-LECGATE-R2 / COUNT-REVOKED owners should fill it.
