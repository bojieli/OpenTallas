# QC-C1O-COMPOSE handoff (updated 2026-11-25 04:12 PST)
Lane: stage + compose QC C1o (child of QC-ALLFIX). C1o is FROZEN (COORD Fable item 25): new rows -> C1p.
C1o v13: plan aa3a14fb7484, sidecar a142fe516f24 (epyc10/epyc12 /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE/c1o_v13). Base C1n-r3 fa8944bb0a39.
Rows: PIPEREACH 0f77, DEMACRO v2 731e98d91d28, STA-RELAY-PRUNE 960d, COLL-IRN-SEAT 3872, HALOCORNER 87eb (+sc), MONLEG e3d0 + RSN 4ceb (+sc), SUL1 1bca (plandiff r2->7ae1; overlay sink_bins/c1o_sul1 x2), BTLAT3 4557 (plandiff r2->4557), DESTACK v2 8562 (7 types), CA-REDERIVE last (= r3 d09c).
Gates: guard PASS 0 silent (3692 intended, c1o_v13/drops.txt), SIDECAR PASS, rreval 0, far 0, FTSITE 3/3, BITSITE 981, ROW-LEDGER PASS (9 key-present, spec_v13.tsv).
PRE (gate): installed tree epyc12 launch_c1o_bind, rt b7165c47a452: PASS findings 0 adv 406 (preF2.sh; log epyc11 preF_v13i.log). By-path PASS adv 407.
Strict bind: unit oth-ubuntu-1131760-1795608596 epyc12, bindO.sh, log epyc11 bindO_v13.log, out epyc12 bind_v13/. On BIND OK: post, then launch.
Sc rows-proof (probe bind, installed tree): proofC13.sh, log epyc11 proofC_v13.log (informational; ROWS-NO-PROOF did not fire).
Launch split (lanes/handoff/QC-C1O-COMPOSE-launch-list.json): 72 HELD (C1p rows), 40 FULL --goal route, 18 PLACE-ONLY probes (st_a/stm C1/C2, cbn C5, sle_su_l1) for FP-CONVERGE-QC. SMELL.tsv / flat-DRT list not found: re-split when they land. QC-DRT-LAYERS GRT M2/M3 default: add to kit wave env before launch (not posted yet).
FWLEAF-1 probe relaunched (OT_PROBE_THROUGH=1) for C1p: private_specs/QC-FWV1-HOLD/..._1125011806.
Scripts (epyc10/epyc12 lane dir): c1o_build6.sh, c1o_rows.py (+plandiff), ca_post.sh, preF2.sh, mkLS.sh, mkB.sh, bindO.sh, proofC13.sh, launchlist.py, ledger_pre.sh.
Cleanup later (ot-delete): intel1 QC-C1O-COMPOSE/tree (57 GB), launch_* dirs.
