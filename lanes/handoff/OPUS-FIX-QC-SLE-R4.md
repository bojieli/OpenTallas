# OPUS-FIX-QC-SLE-R4 handoff (Opus, started 2026-11-21 01:40 PST; succeeds FABLE-FIX-QC-SLE-R3 on the Fable limit)
Family: QC sle_ctl, sle_su_c, slw_su_c* (core-slit station class). Read lanes/handoff/FABLE-FIX-QC-SLE-R3.md and -R2.md first (cause, fix, scripts).
Work dirs epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-sle/{r2,r3}; client logs rtx-pro ~/fable-fix-qc-sle-r2/.
Waiter script (rtx-pro): /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/sle/wgrt.sh TAG CLIENTPID

## State - 11:10 PST. Plan rows -> QC-PLAN-R10. Face-seat class owned by FABLE-FIX-QC-STRAP.
- k_a2 (variant A): GRT overflow 0 (was 40k: core-slit class FIXED). GRT setup repair flat at WNS -75.6 / 558 eps, all u_cland_cws2_i/d[*]; GRT_STOP noconverge rc 21 (unit oth-ubuntu-85854-1795261490 done).
  STA (epyc9 fable-fix-qc-sle/r4a/sta_a/sta.out, 4_cts placement RC): cws2_i port (input delay 245) -> 256.7 ps wire -> u_cland_cws2_i/d FALL capture 416.5 = -123.2. Half-cycle port->landing class = face seat.
  Asked STRAP (post 10:5x) whether their seat rows cover u_cland_cws2_i or I build the private seat variant on k_a. NO blind relaunch of the wave kit.
- k_b2 (variant B, +1 station hc1/hc3): GRT overflow 5; client PID 1285148 in GRT repair; expect the same cws2 class. Waiter on exit (wend.sh).
- sle_stm_v2__cl7b3062fa (taken 10:5x): not superseded. Cause = reset tap, not stations: u_core.rst_n on tap 0 (u_rrl_162), leg 699 um. Row reset.inst_taps {tap 79, sinks [u_core]} -> 190 um, 0 cycles; sibling cl55be2264 tap 51 (643 -> 149). Rows epyc7 opus-fix-qc-sle-r4-rows/stm/stm_rows.json 2b2dfe128b06, posted QC-PLAN-R10 (hub df0abde2). cl7b did not relaunch on R6V1: unchanged block de0257021bf0 holds a STRUCTURAL GRT-0273 struct_stop -> relaunch from the plan event that carries the row. Open: rs2_g->p2l data leg 598 um.
- Variant C (sle_ctl): r4a/p_r4c.json 2655d5d53eb7 = p_r2a + V2 cws2 landing move (y 1257.12) + cws2 ft re-derive (hop 314). rtx-pro ~/fable-fix-qc-sle-r2/launch_c.sh: bind c4 (r2/bind_c4.*) then chain_r2.sh k_c c4 route (client ~/fable-fix-qc-sle-r2/kit_k_c.client.log).
- Patched tap_balance copies: originals tap_balance.tcl.orig_r4 in k_a/k_b gen dirs.
- Pass = 5_1_grt.log overflow 0 (kit runs OT_GRT_ALLOW_CONGESTION=1: read the number), then DRC 0, TT >= -42 ps, FF hold >= 0, LEC; CTS post-hook only.
  Baseline to beat: GRT overflow 40.2k -> 39.0k flat (N46C).
- V2 rows: QC-PLAN-R8 took all R3 rows into plan c5/p_final3 (sle_ctl rows_v2b, su_c s2 x3, slw_su_c__cl19bb38ef s3 = +1 station on l0_o/l0_p1_o/l1_p1_o).
  Their b8 strict bind died rc 2 at 01:47 (theirs to fix). su_c proof starts from the first passing V2 bind (kit-rtl sle_su_c, GEN with plan + rows, pattern r2/kit_r2.sh).

## Waiters armed (this session; a successor must re-arm)
k_a GRT/exit, k_b GRT/exit (wgrt.sh).
