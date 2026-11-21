# FABLE-FIX-QC-SLE-R3 handoff (Fable, started 2026-11-21 00:50 PST; succeeds FABLE-FIX-QC-SLE-R2). Family: QC sle_ctl, sle_su_c, slw_su_c* (core-slit station class)

Read lanes/handoff/FABLE-FIX-QC-SLE-R2.md first (cause, fix, scripts). Work dirs epyc9: R2 = /srv/opentallas-scratch2/claude/fable-fix-qc-sle/r2
(binds, proof kits k_a / k_b), R3 = /srv/opentallas-scratch2/claude/fable-fix-qc-sle/r3 (su_c design, V2 rows).

## State (keep current)
- 00:55 bind_a2 / bind_b2 still running (started 00:36). Launchers rtx-pro PIDs 3921391 / 3921392 alive. No build result yet.
- su_c: kit-rtl of the V1 bind for sle_su_c, slw_su_c__cl19bb38ef, slw_su_c__cl92142dac -> R3/base_<type>/rtl (true sources per bus), design not started.
- V2 base for the rows: epyc9 /srv/opentallas-scratch2/claude/qc-plan-r8/v2b/c4/p_final.json (66f5767294d1), QC-PLAN-R8 bind b7.
