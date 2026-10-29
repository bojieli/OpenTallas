HEAD START export state copy (opt-in, zero cycles)
================================================

Measured need: the hd_tile count-origin s2 state fans out to W reader control
(about18,722) and E forwarded START face flop (about702,513): Manhattan diameter
893um exceeds two405um hops. A single state flop cannot serve both. Exact-neighbour
corridor optimization of2388existing flops leaves that source with450.3um worst
reach, even after its other payload families close analytically.

`ot_dp_landing_origin_s.FWD_COPY` defaults0. With1, the D-side START export uses a
retained parallel copy of the same existing states. Each copy uses the same clock,
synchronous raw reset and predecessor data equation. The original internal start
and PAD/edge sampling stay unchanged. PADW1 adds one FF; PADW2 adds three. The new
parameter-free helper module keeps hierarchy, and each instance is kept, so logic
optimization retains the physical copies. These are DATA-state copies, not clock
pads. The plan's optional `clock.landing_origin_export_copy` boolean emits1 on
strap-form origin instances only; absent/false emits identical wrapper text.

Minimal validation, directly measured and not independently NUMBER-CHECKed:

-49focused generator/face_guard/straps/START/verifier tests PASS.
-Real landing RTL Verilator5.050 lockstep PASS10112 comparisons across64static
 selectors/PAD/edge/root variants, comparing start/start_d/raw with distinct reset
 dates and reassertions;0addedcycles. Unit1897696-1793258000 on intel2.
-A late predecessor on the copied export state fails atcycle24; unit1919939-1793258070.
-Generic Yosys proc/flatten/opt retains9copies across3PADW2origins; unit1936547-1793258120.
 `retention.json` summarizes the retained modules from `preserved.json`.

A legal-corridor placement hypothesis: SF/S0 near354,500; S1near354,400; original
S2near354,710; exportcopy near700,354. All predecessor/raw-reset Manhattan legs
are<=405um, with the export along the lower horizontal channel. Fresh physical
placement, clock assignment, CA margins, synthesized full-tile retention/LEC,
and full graph census remain required. No route, timing, freeze, or release claim.

`make_miter.py` regenerates the bench from the current generator. Compile once
normally, once with `OT_ORIGIN_EXPORT_MUTANT_LATE`, using the real landing RTL.
The initial kit-generation unit-test missing ROM-declaration file was a sparse
checkout dependency; adding tools/mem_compiler fixed it without source changes.

Actual full tile source gate, 2026-10-29:
FWD_COPY1 hd_tile_p synth and face_guard1144/1144(netlist AND ODB)PASS;
LEC EQUIVALENT33708/33708, differs0,undecided0,127.8s. Fresh lec.json
mtime00:28:35PDT (the copied old22:36receipt was explicitly ignored).
Actual new mapped sequential names: exactly1added export FF,0lost old FFs.
Unit epyc2 oth-ubuntu-3564365-1793258734 completed exit0. No CTS/route/STA
claim. Actual physical trial uses kit source hooks, not a changed saved ODB.
