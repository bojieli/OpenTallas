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

## Codex takeover 2026-11-21 16:29 PST

All E7 private native proofs use the V2 b20 event `s29q103S4Q9N46R6V2`. Green bind and all 1,921 native lanes pass for S2 matched zero-egress (2169476), paired q10/q11 reset/corridor (2259371), q01 NB fixed roots (2329784), and the six-type CB zero-cycle site bundle (2500497). The first S2 variant needed explicit source root allowance, while its higher-cycle outbound replacement had native type and landing-inventory splits. The first q10/q11 native attempt applied localization ahead of the existing late `reset.inst_taps` override. The corrected rows edit the existing late overrides. Artifact paths and model limits are in `FAM-QC-CB-R2-V3-cb-candidates.json`. Fresh sealed place and propagated timing remain pending for these forms.

- Actual `df1946805779` CBF q00 S2 and both long q01 variants carry exact ISSUES. The V2 q11/q10 short-pipe and reset diagnostics and physical Q-chain fix are in `results/geom_review/QC-CB-V2-7F3C-2A6C.md`. Shared Q reseat main `91f555583460` and q01 segmented D6 main `25e34125ff37` are merged. q01 sealed spec remains host-drained.
- CBF SerDes measured ordering helper main `687e47d408e`. Per-type path `partition_types.<type>.clock.landing_contract.bands.<band>.pinslot_order`. q01 S2 TX band `lsb_low` now places all 3,444 from pin slots and collapses the failing DCH6 selector's four source X span 462.024 → 1.188 µm. Exact E2 place replay `v2_q01_s2_ring_place` is live. q00 S2 RX `lsb_low` and TX `lsb_high` each convert 3,444 cursor assignments to pin slots on the exact pre-GPL A/B (E7 2991540, `q00_s2_ring_prepl`). Full placed timing pending.
- cf0b exact E2 CTS and local experiments are under `fam-qc-cb-r2/v2_cf0b_cts`. Frozen `cf0b_nab_sweep_r2.log` proved all 3,084 data-latch bypass endpoints at BC FF ≥+52.16 ps and scoped TT −668.48 → −263.41 ps. Current stock TT after bypass instead limits on tap[0] at −607.02, with +211.16 ps from three HB4 and clk_c3 early −1122.10. Type-specific latch source merged main `aaf7e2e482e`. Exact plan `cf0b_typed_nab.json` and native E7 `cf0b_typed_nab_native` (2888511) use fixed pipes and unchanged lane cycles. This row is still private.
- cf0b internal FF −1342.61 is u_rst_in → u_srl_69 via clk_t45, whose 17-sink subtree grew by ~267 ps in each of eight padding rounds after interpreting values 0.351169..0.951777 ps as seconds. Shared fix main `ffce7fc59e2` uses OpenSTA command scale. Exact original 3_place → CTS replay `v2_cf0b_cts_units` is live. Hardware and scope changes remain held for timings and real visual review.
