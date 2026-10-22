# Frozen HB1 native-cell simulation dependencies

Dependency and static identity audit only; no simulation, synthesis, EDA, mapped
source generation, timing qualification or functional PASS is claimed.

The official files in `official/` were read without modification from selected
original host ot-epyc6, immutable image
`openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
under `/OpenROAD-flow-scripts/flow/platforms/asap7/verilog/stdcell/`.
`SEQ_RVT_TT.lib.gz` is deterministic gzip of the exact image file
`/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`.
Its decompressed SHA256 matches the original357fb55e2 frozen inventory:
`57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3`.
BSD license and notices in the official source files are retained.

`manifest.json` pins every original byte hash and joins all64,383 mapped cells
from357fb55e2 receipt/mapped.json.gz to41 official masters, with exact equality
of each instance named-port set and its official module declaration. The source
module directions are recorded, but mapped JSON lacks cell port directions;
this does not claim a fresh native direction audit. There are17,174
DFFHQNx1 and1,178 DFFASRHQNx1 cells. No unknown master or pin mismatch occurred.

Both HQN and ASRHQN outputs are inverted storage: clean rising CLK captures
QN=~D. In ASRHQN, RESETN=0 with SETN=1 asynchronously gives QN=1; SETN=0 gives
QN=0 and dominates simultaneous RESETN=0. The official UDP takes inverted D,
`~RESETN` as its set input and `~SETN` as its clear input. Its clear-priority
truth table agrees with Liberty next_state=!D, preset=!RESETN, clear=!SETN,
clear_preset_var1/2=L. The baseline ties all SETN high. Keep the asynchronous
RESETN sensitivity and QN inversion; renaming QN to a true-Q flop changes data
and reset semantics. At clean binary control values these equations are exact;
the official UDP also has detailed X/edge/notifier behavior that a simple
behavioral DFF replacement would not preserve.

Simulator caveats remain OPEN. The SEQ .v uses Verilog UDPs and delayed_D,
delayed_CLK and asynchronous delayed pins driven through timing-check output
arguments in specify $setuphold statements. There are no direct assignments
from original pins to those delayed wires. Ignoring specify timing-check
outputs can therefore leave the functional UDP inputs undriven. Enabling
specify syntax alone does not establish timing-check-output support. A separate
fleet simulator capability probe should diagnose this before the full miter;
retain its failure and obtain a narrowly scoped projection decision if needed.
No such probe or projection is included here.

The image also supplies `dff.v`, SHA256
`1141a9ddb579a4eaf131bb0fe4a4b44f22c11af54c970a829e9357d9ddfb9313`,
whose own comment calls it a quick replacement for unsupported Verilator UDPs.
It defines only HQNx1/2/3 as posedge QN<=~D, and has no ASRHQN. Do not compile
it together with the original SEQ definitions (duplicate modules), or infer a
complete asynchronous/X-faithful model from it. It is preserved as upstream
context, not selected as a replacement. The five official RVT files form the
complete observed mapped-master dependency set.

Read-only version queries on ot-epyc6 found `/usr/bin/iverilog`12.0 stable and
`/usr/bin/verilator`5.032; these are not the closure daemon required5.050.
No Icarus/Verilator executable was found on the immutable image PATH or its
`tools/install` subtree within the bounded inspection. The eventual runner
must pin its actual executable/version and use the coordinator admitted fleet
installation. No simulation or compile was run for this audit.


## Separately requested functional projection

The parent explicitly requested an exact Liberty-driven simulation-only
projection after the official delayed-pin limitation was identified.
`generate_functional.py` reads the five original compressed Liberty files,
checks every used cell port and direction against the41-master ledger, and
emits `functional_projection.v` plus source-function/hash ledger
`projection_manifest.json`. The source4 combinational library gzip files are
copied byte-identically from the same immutable image. The sequential source
is the frozen SEQ Liberty above. Every combinational output uses its exact
Liberty Boolean function; !/*/+ translate to bitwise ~/&/| on scalar pins.
The generator only parses text and emits64,383-instance master dependencies;
it performs no synthesis, simulation or mapping.

This projection is UNVALIDATED and restricted to binary clock/reset/set
controls with CLK initially established low before the first measured rising
edge. It intentionally makes no equivalence claim for uncertain clock edges,
unknown async controls, notifiers, timing violations or SDF delays. Unreset
storage remains uninitialized. ASR uses the exact clear-first/preset-second
truth function and records previous CLK to distinguish a real0-to1 clock
transition from control deassertion. Watching both control polarities matters:
SETN0-to1 while RESETN remains0 must change QN from0 to1 immediately; a normal
negedge-control-only DFF model would incorrectly miss that transition. Control
release with both controls high holds QN until the next clean rising clock.
These event choices still require the planned standalone fleet checks in
projection_manifest.json before use as a faithful miter dependency.

The planned checks cover every combinational input combination against original
primitive gates, clean data capture/hold, asynchronous assertion and release at
both CLK levels, simultaneous controls and priority, release from both low,
and original UDP comparison under a separately approved delayed-net alias
projection. No such checks or simulation have been executed by this task.
