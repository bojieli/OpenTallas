# HEAD padding-state preservation — disabled native fragment PREP

This packet adds no production RTL change and launches no job. `run_disabled.sh` exits70.
The fourteen original raw failures remain. This is a possible bit-exact implementation
repair, to be tested before choosing the separately held idle-padding clamp/refinement.

## Exact source recurrence and scope

Current u_wtx is W110/N2/P62/MUT0/IDLE_ZERO0. Project `hold[61:48]` and
`oq_p[61:48]` (fourteen bits), with `b0=d[61:48]`, `write=start|owe`:

- `q_next = write ? 0 : q`, with **no reset/initial value**.
- `o_next = start ? b0 : q`, with no reset/initial value.

This projection preserves the actual fourteen **second-beat** padded bits. First-beat
bits48..61 are real data and remain arbitrary b0, not forced zero. The input cut keeps
start/owe/b0 arbitrary; no new source reset/valid/transaction assumptions are introduced.
The existing output fourteen flops are retained; only the missing hold-state dimensions
would be restored. Source functions/cycles remain unchanged.

## Actual synthesis vehicle found

The exact image's `synth_canonicalize.tcl` sources **existing**
`SYNTH_CANONICALIZE_TCL` after hierarchy and before opt_clean/canonical RTLIL. The
main `synth.tcl` later invokes coarse synth, fine synth, opt -purge, native mapping,
opt, setundef -zero, ABC and opt_clean. A post-synth patch is too late.
`SYNTH_KEEP_MODULES` only sets module keep_hierarchy. It does not by itself retain
constant-clear state within the module.

Repository `physical/common_flow/ot_keep_regs.tcl` is a real pre-opt hook: proc,
selected FF techmap to per-bit cells, then cell KEEP. Its recorded qualification is
for duplicate FF merging, not this unreset enabled constant-clear recurrence.
`generic_cell_keep_hook.tcl` uses that hook on the exact projected state wire; it is
a **probe, not a qualified fix**. It must retain14 independent free initial states
through all later passes. The direct `cell_keep_probe.ys` is a supplementary early
cell-attribute probe, not the preferred full-flow hook.

The image contains no Yosys C++ sources and reports 0.68+post with UNKNOWN git SHA.
Upstream current opt_dff source has no general FF-cell KEEP bypass; wire KEEP tracks
mux users rather than universally blocking constant-state removal. This is a reason
to test the exact pinned binary, not evidence that its behavior is identical to main.
Sources: [Yosys opt_dff](https://github.com/YosysHQ/yosys/tree/main/passes/opt/dff),
[attribute documentation](https://github.com/YosysHQ/yosys/blob/main/docs/source/using_yosys/verilog.rst).
No broad -keepdc or global optimization policy change is proposed.

## Default-OFF alternatives and negative controls

`pad_fragment.sv` defaults to mode0 (unpreserved baseline). Mode1 tests wire KEEP/DNT;
mode2 tests a kept generic leaf, still optimized internally. Separate mode0 plus
`generic_cell_keep_hook.tcl` tests the **real per-bit cell KEEP recipe**.

Mode3 instantiates fourteen existing native `DFFHQNx1_ASAP7_75t_R` cells. For each,
`D=~(QN|write)`, `q=~QN`; thus q_next=write?0:q exactly. The new native cells are
KEEP/DNT and library blackboxes during synthesis. They must survive normal mapping,
post-map opt and ABC. This is a concrete fallback, not an assertion that a module
name alone retains state. Gold q_i maps bijectively to physical ~QN_i; all14 initial
coordinates remain independent and unrestricted. `native_ff_model.sv` is used only
for the source-relation coupon, never with Liberty in SYNTH. It has no initializer.

`fragment_mutants.sv` includes wrong complement, forced initialzero, missing owedclear,
and clear-to-one. The missing-owed-clear control targets the unconstrained **cut**
recurrence; it is not asserted to be a reachable full-transmitter reset trace.
All controls must reject under their declared initial/state scope. Baseline's actual
folding is a required negative preservation control; no presumed cell count is PASS.
A future native coupon must check initial-state bijection and raw idle outputs, not
only valid outputs or structural counts. No old12732 prior, output mask, hints, new
DC, reset assumption, solver policy or whole-84750 verdict is modified.

## Concrete physical budget before adoption

+14 unreset FF, +14 CLK pins, **0 reset pins, 0 cycles**. Native observed
DFFHQNx1 body1.08x0.27um (0.2916um2): FF body delta4.0824um2. Each needs
one clear/hold feedback gate. QN can be absorbed into output mux logic; no logical
Q inverter is assumed free. An explicit constructive implementation per bit uses
one NOR2 feedback and an output mux built from two NAND2 plus one OR2, replacing
the current start&&b0 AND2. At observed0.324x0.27um simple-gate bodies, this is
+14FF +42 net simple gates = **7.75656um2** before shared enable buffering,
resize/tap/clock distribution and routing. This is a constructive static estimate,
not a measured mapped result; ABC may use other native cells. A literal q inversion
implementation must count its fourteen INV cells (observed0.162x0.27um) explicitly.
Actual fragment mapping decides mux/inv/body counts. `PHYSICAL_COST.json` pins the
observed dimensions to an existing native geometry dump, not a new CAD trial.

The fourteen clock capacitances add to the existing wtx cohort; no new reset cohort.
A later production event must place the14 cells beside their current oq_p producers,
price the feedback/start fanout and PG terms, update all clock sinks, and LOOK/check
actual geometry and related-pair timing. No location, clock fit or timing PASS is
claimed by this packet. Source/cohort adoption and all current physical holds stay.

## Narrow execution proposal, still disabled

One 4GB/1T/disk1 normal ot-run coupon using exact pinned image, existing native Libs
and mapping readset: baseline → wire KEEP → per-bit cell hook → kept generic leaf →
explicit native leaf, preserving all normal optimization passes. Measure FF/cell/body/
CLK/PG inventory and then source-lockstep initial-set relation with the four mutants.
Record intermediate pre-opt/post-opt/post-map artifacts and no-init/no-reset checks.
Fill exact selected Lib/config hashes before execution. No full HEAD SYNTH, P&R,
STA, new formal job or source/default adoption is authorized by this packet.
