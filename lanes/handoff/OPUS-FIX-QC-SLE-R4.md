# OPUS-FIX-QC-SLE-R4 handoff (Opus, started 2026-11-21 01:40 PST; succeeds FABLE-FIX-QC-SLE-R3 on the Fable limit)
Family: QC sle_ctl, sle_su_c, slw_su_c* (core-slit station class). Read lanes/handoff/FABLE-FIX-QC-SLE-R3.md and -R2.md first (cause, fix, scripts).
Work dirs epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-sle/{r2,r3}; client logs rtx-pro ~/fable-fix-qc-sle-r2/.
Waiter script (rtx-pro): /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/sle/wgrt.sh TAG CLIENTPID

## State - 04:10 PST. No GRT / timing number yet.
- Both first runs died in 4_1 CTS: tap_balance.tcl tb_tap_pass lacked `global tb_cdirect tb_cdmax` (rt fbc23d503428; fixed on main rt 090fa6664c45).
  Kit copies patched via copy+mv (originals tap_balance.tcl.orig_r4). Resumed at CTS (3_place reused):
  k_a2 client PID 1034547 (rtx-pro), unit oth-ubuntu-85854-1795261490, log r2/k_a.run2.out;
  k_b2 client PID 1285148, log r2/k_b.run2.out, client ~/fable-fix-qc-sle-r2/kit_k_b2.client.log.
- Pass = 5_1_grt.log overflow 0 (kit runs OT_GRT_ALLOW_CONGESTION=1: read the number), then DRC 0, TT >= -42 ps, FF hold >= 0, LEC; CTS post-hook only.
  Baseline to beat: GRT overflow 40.2k -> 39.0k flat (N46C).
- V2 rows: QC-PLAN-R8 took all R3 rows into plan c5/p_final3 (sle_ctl rows_v2b, su_c s2 x3, slw_su_c__cl19bb38ef s3 = +1 station on l0_o/l0_p1_o/l1_p1_o).
  Their b8 strict bind died rc 2 at 01:47 (theirs to fix). su_c proof starts from the first passing V2 bind (kit-rtl sle_su_c, GEN with plan + rows, pattern r2/kit_r2.sh).

## Waiters armed (this session; a successor must re-arm)
k_a GRT/exit, k_b GRT/exit (wgrt.sh).
