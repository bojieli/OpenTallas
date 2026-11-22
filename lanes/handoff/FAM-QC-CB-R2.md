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

## 07:5x
- fp8 GEN DONE rc 0 (epyc7 fam-qc-cb/proof/fp8/gen/cbf_q00__cl1b5a6458). RTL verified: x_0_1 on rst_n_t77, x_1_1 on rst_n_t76.
  It CANNOT be placed: hand-built GEN with no kit_env_provenance.json, so run_kit.sh exits 14. Its env also lacks wave OT_CELL_WAIVER=r703.
- Rows -> QC-PLAN-R10: lanes/handoff/FAM-QC-CB-R2-rows.json (V2 if possible, kit-rtl applies without a rebind; else V3).
- private-spec always takes kit_rtl.bind_out from the wave (V1 v1r6_bind_1120193410). No private bind can feed it, so a proof
  that needs the R8 link_sites RTL (lane-pad depth) must wait until V2 is the wave plan. The alternative is a --bind-out option in private-spec (COORD/FLOW-PROC-A decision).
- V2 b17 strict bind RC1 (TYPE_SPLIT sle_ctl). R10 b18 bind is running on epyc7 (ot-run client pid 3273671).
- Next: when V2 is applied, run private-spec qwen_compute cbf_q00__cl1b5a6458 --plan <V2 plan + rows> and run-item, then wait with ot-wait --kit place;
  check that the reset-relay -394 class is gone, then route and sign off. Then relaunch cbn_q01__clab6e67f2 and the siblings on V2.

## 09:1x
- p1/b1 private strict bind: b16 plan with cbf_q00 inst_taps t24/t25/t77/t76. Clean: errors 0, LATCHECK 1921/1921 (epyc7 fam-qc-cb-r2/p1/b1).
  A rebind is required: inst_taps sit in the native reset contract, so kit_topology reports BIND_STALE without one.
- cbf_q00 rep kit: private-spec --tree p1/b1/tree --bind-out p1/b1/bind --host epyc7 --src-manifest off. Spec at p1/spec2, place started 08:49.
  It was generated BEFORE main 3ed87c352a (FLOW-PLACEMEAS), so its post-place WNS still includes recovery and the ideal landing term.
  Judge it from CTS (cts_read.py / post-hook 4_cts_final), not from the place number.
- cbn_q01__clab6e67f2 kit: same bind, spec at p1/spec_cbnq01, place running. Its tcl is NEW (recovery split out), so the post-place number counts.
- Private kits are exempt from PLACE-SETUP-STOP (lane proofs).
- R10 b18 bind died: bind_b15.sh's RR points at rt/7ff721a00978/r8_refresh.py, which no longer exists. Posted to R10.

## 13:0x
- V2 applied (s29q103S4Q9N46R6V2). The V2 wave attempts of cbf_q00__cl1b5a6458 and cbf_q01_s2 went FAIL INFRA (restaged) with no relaunch.
  I relaunched both as private-spec kits with defaults (V2 plan, tree qwen_compute_v2r10, wave bind, src_manifest on, env=wave) on epyc2.
  These are the SIGNABLE builds. Specs and logs: intel2 /srv/opentallas-scratch2/claude/fam-qc-cb-r2/v2/<type>/.
- I own cbf_q01_s2 (claimed from DEAD-OWNER FAM-QC-CB).
- TAP CORRECTION: keep RRGEN-R3 cbf_q00 taps t24/t25/t93/t100. On V2 geometry they measure 100/90/67/68 um; t77/t76 measure 455/640 um.
- FABLE-PD-QC-1230 item 5 -> QC-PLAN-R11. Still to do: +1 station rows for bc_i00/bc_i10/bc_i30, nb_i12, y_o00, and the cbn_q01/sibling taps, all from the p1 CTS reads.

## STAND-DOWN 18:2x PST -> FAM-QC-CB-R3 (context ~290k)
Read CODEX-LOG.md from line 14146. Codex ran many jobs under FAM-QC-CB-R2 between 14:23 and 18:1x; adopt them:
- In fam-qc-cb-r2/ on epyc2/epyc7: q01_s2_reset_native, cts_copy_q01_s2.sh (v2_q01_s2_cts.log), q01_serdes_ring_place, glue_exact_chunk, native_bind_s2.sh v3_*.
- CODEX-LOG 14211: q01 S2 reset-inclusive strict bind, 130 types, 1921 lanes. TT +18.75, TNS 0, internal FF -31.03, no route.
- CB q01 repeated cut: 514 over-cycle paths at 765/846 um, both HELD. Retained cf0b TT corrected from -659.86 to -380.66 on the stage SDC.
- Old CB q01 cldd6: watchdog rc143 after true TT -321.75, exact CTS -323.16.
My own kits. Every run-item ENDED at stage geom PASS, so no CTS ran and cts_read reports UNMEASURED:
- p1 cbf_q00 and p1 cbn_q01 (private bind fam-qc-cb-r2/p1/b1, epyc7).
  Place proved the reset-relay class gone: relay -> fabric +300.7 and +631.5.
  Worst on both is -380.83, the ideal-clock latch -> core pin term.
- v2 cbf_q00__cl1b5a6458 and v2 cbf_q01_s2 (signable defaults, epyc2): placed, geom PASS.
  Next: CTS / route them to sign-off, using run_kit GOAL=route on the kit or the wave relaunch. Read the CTS post-hook.
Open: FABLE-PD-QC-1230 item 5 rows -> QC-PLAN-R11 (successor of R12?).
- Taps: keep RRGEN t24/t25/t93/t100, measured on V2 geometry.
- +1 station rows (bc_i00/bc_i10/bc_i30, nb_i12, y_o00) still to write from the CTS reads.
- cbn_q01 taps: OK on attempt_17 positions; recheck on the V2 placed DB.
Waiters: none of mine are live (the cbn CTS ot-wait timed out at rc 124).
