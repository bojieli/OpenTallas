# FAM-QC-CB-R2 handoff (started 2026-11-21 07:0x PST; succeeds FAM-QC-CB)

## State 07:2x
- Rep cbf_q00__cl1b5a6458. fp7 + V1 paired bind (v1_paired_r3) DIED 06:1x. Not re-running V1 bind (TYPE_SPLIT hc0 + EMIT = class fixed by R9 b15).
- RRGEN-R3 inst_taps t93/t100 for x_0_1/x_1_1 measure 525/506 um on fp3 positions (leaf-leg checker, epyc8 lanes/ll-out/cbf_q00_fp3pos.json).
  Re-picked (fam4/b17 tap numbering): x_0_0 t24, x_1_0 t25, x_0_1 t77 (75 um), x_1_1 t76 (135 um), 0 cycles.
- fp8 GEN epyc7: /srv/opentallas-scratch2/claude/fam-qc-cb/proof8.sh cbf_q00__cl1b5a6458 fp8 fam8_plan.json (log fam-qc-cb/fp8.log, ot-run pid 2647117).
  proof8 = proof5 + rewrite of qc-plan-r6/v1/b_n4/tree -> $O/tree in staged rtl (the fp5-fp7 rc=22 cause).
- Lane clone (tools cone): epyc7 /srv/opentallas-scratch2/claude/fam-qc-cb-r2/clone.

## Next
- fp8 GEN ok -> kit via kit_wave.py private-spec (needs rt >= 17b1273352de) -> place: check -394 reset path gone -> route -> sign-off gates.
- Signable: V2 b17 bind (QC-PLAN-R10, epyc7 qc-plan-r9/b17) carries the OLD t93/t100 rows; re-picked rows go to QC-PLAN-R10 as V3 rows.
- cbn_q01__clab6e67f2 held at 17-attempt cap (u_rrl_515 -> x_0_2); re-pick its taps on placed positions the same way, then rows to R10.
