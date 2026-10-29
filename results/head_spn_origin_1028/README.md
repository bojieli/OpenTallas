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

- Focused generator, face_guard, straps, START and graph-verifier tests: 46 PASS.
- Real source `rtl/common/ot_dp_clk_landing_ca.sv`, Verilator 5.050 lockstep:
  10,112 comparisons across 64 static selector/PAD/edge/root combinations,
  including different raw-reset dates and reassertions. Zero mismatches and zero
  added cycles. Run intel2 `/srv/opentallas-scratch2/claude/codex-head-spn-1028`,
  ot-run unit `oth-ubuntu-1189509-1793256485`; retained `miter.log`.
- Wrong input on the first origin: mismatch at cycle 24, caught by the same
  miter (unit `oth-ubuntu-1218661-1793256560`; retained `mutant.log`).
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
START cones (PADW=2 miter: 6 flops per added origin); no additional external pin.
