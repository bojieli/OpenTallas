# vK: one output pin cycle for program fault

Collected vI ECO i1: NOT SIGNED TT -44.08ps/4 endpoints, FF +0.21ps, slew29TT/27FF, cap0, DRC0/antenna0. One physical ECO completed; attempted i2 staging was blocked before creating a physical pass. No second ECO will run.

GEOMETRY / CLASS DEPTH+REACH: actual worst TT starts digest[38], crosses five buffer stages, then XOR and eight reduction/control stages, then drives the output face fault FF at(5.02,121.23). The duplicate internal fault FF at(131.49,89.37) computes the identical next-state _3129_ locally. The face receives the whole logic cone across about130um; the internal state is already nearby. Actual vI final density/macros/clock endpoint-span image viewed; no host-fence congestion ring remains. Macro gap addressed separately by vJ2 channel widening retained in vK.

REDESIGN: replace only `else u_program__fault <= _3129_;` with `else u_program__fault <= hrfp_u_program__fault_0_internal_state;`. PIN CYCLES: +1 on u_program__fault output only, in addition to inherited footer+1, read response+1, reset release+3. Internal fault state and all feedback remain byte-identical. The exact source scan finds only the five declaration/assignment/reset/output-list references to the public output; no logic consumes it. Parent/compiler/token must observe that fault pin one clock later.

Estimate: this separates the deep compare from the long output reach. Existing internal fault flop computes the same compare locally; the new face path is clock-Q plus about130um buffered wire, with the full833ps cycle. No new register, area, macro, clock or internal handshake cost. No timing claim until measured.

Smallest vehicle extracts BOTH actual old/new always blocks from full RTL and treats the unchanged combinational next-state cone as arbitrary input. 270-cycle lockstep PASS with first fault, sticky assertion, deassertion, mid-fault asynchronous reset and repeated pulses; all internal state equal, output equals the old output one edge earlier. Bypass mutant (zero added cycle) fails116 comparisons. Reset-leaf equality relies on the inherited B8 R1 proof; the tree is byte-identical. Full candidate mapping LEC remains required.

One PLACE pilot only. Before route: view actual density/macros/pins and clock reach; no batch release.
