# ASAP7 predictive physical implementation

**Campaign:** `opentallas-asap7-predictive-physical-v1`  
**Overall status:** **PARTIAL**  
**Completed cases:** 2/3  
**Clean-baseline cases:** 2/3  
**Stale archived cases:** 1/3

This is a source-hashed RTL-to-GDS experiment in the public predictive ASAP7
research platform. It is not foundry signoff and contains no ROM or SRAM macro.
The bundled ASAP7 FakeRAM files are explicitly forbidden from these cases.

## Results

| Case | Status | Canonical | Target | Fmax | Std-cell area | Routed wire | Vias | Setup WNS | Hold WNS | DRC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `numeric_e1_l16_tc` | PASS | yes | 235.3 MHz | 243.1 MHz | 632.34 µm² | 10832.0 µm | 42366 | 0.1369 ns | 0.8051 ns | 0 |
| `numeric_e4_l16_tc` | PASS | yes | 83.3 MHz | 83.6 MHz | 2603.30 µm² | 80823.0 µm | 202497 | 0.0413 ns | 2.3635 ns | 0 |
| `reduction_s8_g2_tc` | STALE | yes | 444.4 MHz | 455.3 MHz | 845.51 µm² | 22184.0 µm | 61473 | 0.0535 ns | 0.0558 ns | 0 |

A case is passing only after mapped-netlist and final-netlist sequential
equivalence, zero reported setup/hold violations, zero detailed-route DRC
errors, zero antenna violations, and zero flow errors. A dirty-worktree run
is retained as useful source-hashed evidence but does not close the clean-baseline gate.
A STALE case's archived record was produced from source that no longer matches
the lock; its figures describe that older RTL and are not counted.

## Evidence boundary

- ASAP7 is a predictive research PDK and is not tied to a foundry.
- The three cases contain no ROM or SRAM macro; bundled ASAP7 FakeRAM collateral is forbidden and unused.
- The numeric cases implement signed integer DV only, not OpenTallas target MXFP4 x FP8, FP8 x FP8, BF16, or FP32 arithmetic.
- Passing results constrain public digital-cell and routed-wire plausibility only; they do not validate target ROM density, energy, sense margin, power delivery, package, HBM, yield, or manufacturability.
- The reported TC model is the ASAP7 library's nominal model condition and has no calibrated error bar against TSMC N7 or N4.

## Stale archived evidence

- `reduction_s8_g2_tc`: The archived 455.262 MHz / 845.509 um^2 record routes the serial-chain reduction that 4690d6ce replaced with balanced per-group add trees hoisted out of the clocked process (a synthesised-logic change: eight chained 35-bit carry-propagate adds become three levels). 70604b86 then added only a comment and a Verilator lint_off/lint_on UNOPTFLAT pragma pair, which cannot change synthesis. The record therefore describes RTL that no longer exists. Re-qualification: Attempted 2026-09-26 with tools/run_asap7_physical.py --case reduction_s8_g2_tc at this lock (clean tree, remote worker, identical container). ORFS synthesis completed, but the governed mapped transition-relation proof did not close: ABC 'cec' of the 687-output transition relation (677 inputs) was killed by the runner's 1,800 s budget, so place and route was never reached. The same AIG pair was also UNDECIDED under dcec (313 s), &cec (553 s) and the arithmetic checker &acec (545 s, arithmetic boxes not matched), and cec -C 10000000, cec -p and cec -p -s -C 1000000 were still undecided after 86 minutes; cec -p stalls on a single-output cone of 600 inputs and 9,618 AND nodes. The cause is structural: ORFS merges each group's pairwise add tree into one multi-operand carry-save tree (366 FA and 69 HA cells after extract_fa), which shares no internal equivalence points with the RTL's pairwise adders. Re-lowering the gold with ORFS's own synth word-level script did not make the proof tractable either. Closing this needs a proof method for multi-operand arithmetic, not a longer budget.

The next physical stages are exact target-format arithmetic, the stage-control
shell, hierarchical router/NoC cuts, and a separately characterized research ROM
macro. These three initial blocks do not close those gates.
