HEAD multi-input count-origin repair (2026-10-28)
================================================

`hd_spn` previously selected its parent START before one sampler. The sampler D
cone consequently included two independently declared ring START inputs, so
face_guard correctly rejected both. The generator now creates one existing
`ot_dp_landing_origin_s` per possible tree input, with that bus's raw reset,
and selects their outputs using the existing static `strap_ca_tsel`. Single-input
types are unchanged. No register stage or cycle is added to the selected path.
An invalid selector still selects the last bus, as before. The shared graph
verifier follows the selected origin and checks the additional origins' local
clock, raw reset and bus START connections; older generated binds remain readable.

Minimal gates (direct tool results, not independently NUMBER-CHECKed):

- Focused generator, face_guard, straps, START and graph-verifier tests: 47 PASS.
- Real source `rtl/common/ot_dp_clk_landing_ca.sv`, Verilator 5.050 lockstep:
  10,112 comparisons across 64 static selector/PAD/edge/root combinations,
  including different raw-reset dates and reassertions. Current-main API also checks
  `start_d` (D-side forwarded START face flop) and the selected raw reset. Zero mismatches and zero
  added cycles. Run intel2 `/srv/opentallas-scratch2/claude/codex-head-spn-1028`,
  ot-run unit `oth-ubuntu-1319647-1793256795`; retained `miter_current.log`
  (earlier pre-merge API receipt also retained as `miter.log`).
- Wrong input on the first origin: mismatch at cycle 23, caught by the same
  miter (unit `oth-ubuntu-1370014-1793256854`; retained `mutant_current.log`
  (earlier pre-merge receipt retained as `mutant.log`)).
- Two-ring gate-netlist face_guard fixture: separate origins PASS; shared-origin
  mutant FAILS. No face_guard rule was relaxed.

`make_miter.py` regenerates both SV vehicles from the current generator. Run
the generated `miter.sv` or `mutant.sv` with the real landing RTL as second source.
The initial focused-test failure was assertion whitespace only and was corrected.
An initial ot-run submission using `--hosts intel2` was NOT RUN because the hub
has no self SSH alias; `--hosts localhost` is the intel2 hub's actual self alias.

Scope: shared-tool source repair only. No physical plan, pin, latency, clock
arrival, geometry or SIGNED claim changes. HEAD owner must regenerate the resized
spine kit, collect actual synthesized face_guard/LEC and visually review it before
routing. Static selection trades duplicated inactive sampler state for independent
START cones (PADW=2 miter: 7 flops per added origin); no additional external pin.

Current-main integration: fetched origin/main `6b03fc6b2`, manually resolved the
start_d generator hunk preserving both meanings, and repeated the exact miter.
Own branch merge `f97867594`. No main checkout was edited.

Actual hk3 hd_spn mechanism synthesis is running in the same remote lane under
`actual/`, unit `oth-ubuntu-1366313-1793256850` (`run_kit.sh ... synth 32 8`).
This is synthesis/face_guard/LEC only, no P&R/STA on the obsolete hk3 outline.
`actual_hd_spn_origin.patch` is its generated source change. Original face_guard
FAIL is preserved under remote `original/face_guard.json`.

Actual hk3 spine mechanism run COMPLETED exit0: face_guard PASS6224/6224 on
synthesized netlist AND synth-ODB export; LEC EQUIVALENT30456/30456, differs0,
undecided0 (294.8s), port_bind6311/6311PASS, fanout29175regs/0over64.
These artifacts qualify the sampler repair, not the obsolete outline.
