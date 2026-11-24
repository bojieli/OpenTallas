# QC-ALLFIX handoff (integrator + family, die QC)
Brief: scratchpad allfix_brief.txt (+ITERATION LOOP). Base C4 81fd3e6370c0. Table lanes/ALLFIX-QC.tsv.
Work dir: epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX (OT_LANE=QC-ALLFIX). rt 70b6f0430ea9.
- compose A plan = b25b1cf7c404 + cbn_q00 tapoff fill = cA/rows/plan_b25_tapoff.json f418c1b290f3 (census PASS).
- cA/tree = ot-tree-fork of kw45/snap_qwen_compute/qwen_compute_v4c4 (C4).
- Helpers: QC-ALLFIX-SU (su_c re-floor, SU-2, RED+2, rc103, RHI su_l1), QC-ALLFIX-COLL (coll_core reset clock-open, coll rows, SLE CTL B_TW + clock entry).
- QC-V4 keeps RSN FLT (tools bug, kit regen on c84f) + seal/apply. Adopted from QC-V4: b25 strict, RED+2, F16 (f16_physical_1536 + combined_abi_1554: PRE FIXEDCYC lane glue__f16_auth_f16_auth missing latency row), SU-C next form, rc97 narrow parent.
