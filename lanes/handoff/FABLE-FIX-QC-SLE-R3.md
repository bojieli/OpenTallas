# FABLE-FIX-QC-SLE-R3 handoff (Fable, started 2026-11-21 00:50 PST; succeeds FABLE-FIX-QC-SLE-R2). Family: QC sle_ctl, sle_su_c, slw_su_c* (core-slit station class)

Read lanes/handoff/FABLE-FIX-QC-SLE-R2.md first (cause, fix, V1 scripts). Work dirs on epyc9:
R2 = /srv/opentallas-scratch2/claude/fable-fix-qc-sle/r2 (private binds, proof kits k_a / k_b); R3 = /srv/opentallas-scratch2/claude/fable-fix-qc-sle/r3 (V2 rows, su_c design).
Client logs / launchers on rtx-pro ~/fable-fix-qc-sle-r2/.

## State (keep current) - 01:25 PST. NOTHING IS PROVEN BY A BUILD YET: no GRT, timing, sign-off or export number exists.
sle_ctl proof (V1 base p_h.json + R2 delta):
- A (0 cycles): strict bind_a2 PASS 01:00 (bind errors 0, LATCHECK 1921/1921). Kit k_a GEN PASS (PROOF_GEN_RC 0, KIT_PREFLIGHT PASS), run_kit route running
  since 01:09: unit oth-ubuntu-89209-1795251668, client PID 3921391 (rtx-pro), kit R2/k_a/gen/sle_ctl__cla4f6f12f, log R2/k_a.run.out.
- B (hc1 / hc3 +1 station): bind_b2 = R8_STALE only (38 rows, u_tap.hw bound 10 vs table 9). R8 re-derived (R2/r8_r2b.json ddc6d89c6894, qc_r8_pinned
  derive --like r8_v1a) and strict rebind b3 running since 01:05 (R2/b3.sh; client PID 4019656; rc R2/bind_b3.rc, log R2/bind_b3.log).
  Launcher PID 4019657 (launch_kit_r3.sh) starts k_b on rc 0 (client log kit_k_b.client.log).
- Baseline to beat: GRT overflow 40.2k -> 39.0k flat (N46C), TT -1.82. Pass = 5_1_grt.log overflow 0 (kit runs OT_GRT_ALLOW_CONGESTION=1: read the number),
  then DRC 0, TT >= -42 ps, FF hold >= 0, LEC; read CTS post-hook only; export AGIdock + rtx-pro.
- If GRT stays > ~2k: R2 handoff lists the ranked suspects (channel cut x 358-514 at y ~400 first).

V2 rows (candidates, static evaluator only, handed to QC-PLAN-R8 01:2x as "apply before the final V2 bind"; base = v2b/c4/p_final.json 66f5767294d1):
- sle_ctl: R3/sle_delta3.py (copy lanes/handoff/FABLE-FIX-QC-SLE-R3-sle_delta3.py) = the R2 delta made generic in the station counts (V2 has
  hc1 7, hc2 9, hc3 8, st_a_o 4 ...), cws1 / cws2 sites re-derived from the V2 landing-macro position, sites in the 30-um pin-row strips slid out.
  Run: R3/v2rows.sh PLAN TAG (makes ev_v2.pkl once; delete it if the V2 type pins change). Output R3/rows_v2b.json 25b35b0b8ae9, rep_v2b.json:
  0 sites in a core, 0 routes over u_tap / u_ctl, worst hop 291 um (x_fw_p2_i pad), 0 cycles; cws1 hop 338 um, cws2 314 um (V2 before: 351 / 375);
  30 plan points pushed out of the moved boxes. Core moves change the reset identity: V2 needs its strict bind + LATCHECK AFTER these rows.
- su_c: R3/su_delta.py (copy lanes/handoff/FABLE-FIX-QC-SLE-R3-su_delta.py), run R3/su_run.sh PLAN TAG type... (env MAXHOP adds stations).
  No core moves and (default) no station-count change: sites only. Per bit, from the TRUE source in the bound RTL (u_bout_<bus> .d concat):
  x_su_l0_o (su8 gb / pd1 / lv1 / gv + soft): su8|ch gap -> street lower band y 282-308 -> E margin.
  x_su_l0_p1_o (vm8out oa/ob/oc/ocl at their memory cores' q faces + su8 pd1): street band y 351-370 -> E margin; och over ch, between bt and red.
  x_su_l1_p1_o: street band y 374-392 west -> W margin; och / pd1 down the pg|su8 gap.   x_ctl_o: su8 bits up the pg|su8 gap and over pg; red bits
  under red, up its W side.   x_sc_o: under red, up its W side, east above it.   In-bus pads x_ctl_p1_i / p2_i / x_su_l0_i / x_su_l0_p1_i: regs_um
  (packed model) on a core-free centre line (2-8 of them were inside cl / vc / bt / ch); the per-bit in-bus model is NOT re-sited (pad depth D
  comes from the bind, per variant).
  Results on V2 (R3/rep_v2_s2.<type>.json; all: 0 sites in core, 0 routes over cores, 0 cycles):
    sle_su_c            rows b84307a2499d  worst hops l0_o 219, l0_p1_o 236, l1_p1_o 255, ctl_o 300, sc_o 289
    slw_su_c__cl92142dac     194c89fb6df9  226, 230, 306 (ocl -> W face, 3 stations), 300, 289
    slw_su_c__cl19bb38ef     a3f0d2214d2f  377, 345, 408: this variant is under-stationed for its true sources (the V2 counts 2 / 3 / 2 were
      priced on a leaf that is not the source). Alternative R3/rows_v2_s3.slw_su_c__cl19bb38ef.json 3d3a7f3498e7 (MAXHOP=310): +1 station on each
      of l0_o / l0_p1_o / l1_p1_o -> 283 / 276 / 306 um, lanes sl_W0_su_c__x_su_c_su_l0 / _su_l0_p1 / _su_l1_p1 +1 cycle (needs the bind).
- su_c proof: NOT started. Needs a passing V2 strict bind (QC-PLAN-R8 b7 died R8_STALE 01:05; next is theirs). Then: kit-rtl of sle_su_c from that
  bind, GEN with the plan + rows (pattern R2/kit_r2.sh with P/A/C of the V2 tree), run_kit route at --priority plan on epyc9.
- V1 wave kits of the su_c types (not mine, keep running): slw_su_c__cl19bb38ef a2 epyc7, slw_su_c__cl92142dac a2 intel1, both in place at 01:00;
  a waiter reads their GRT overflow: it tells whether the class bites su_c without the fix.

## Waiters armed (this session; a successor must re-arm)
k_a GRT / exit; bind b3 + k_b GEN; V1 su_c wave kits GRT.
