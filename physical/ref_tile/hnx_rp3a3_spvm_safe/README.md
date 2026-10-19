# Independent P3 shared merge safe reset variant

Baseline SRAM gate1003344 continues as evidence in its original tree. Its mapped netlist retains16 separate adder reset flops, each driving432 RESETN pins; rst_e drives454. These copies were NOT merged, and they do not satisfy the32-load target.

This independent kit enables OT_FP_DATA_NORST: the existing adder DRST0 implementation resets valid bits only. The adder already qualifies fault by valid_out; consumers use the fixed valid return schedule. Stale data and err during invalid cycles are unobserved. OT_HNX_ATT_SAFE_RESET additionally creates explicit kept ot_rst_split vector families:32 copies of the wrapper rq edge,16copies of each existing smerge control reset edge and16copies at each adder's existing rst_m edge. All copies have identical D/clock and no additional edge or latency. The main reset_relay_split pass proves identical flops and distributes consumers with max_loads32; TSV plus mapped RESETN counts must independently confirm the bound before item3 PASS. No manual waiver.

Data latency, reset-release latency, protocol and II stay unchanged. The source bench has explicit HNX_ATT_SAFE_RESET=1 selection, records safe_reset=true and isolates its Verilator binary directory. Both defines are opt-in, off by default.

Same432square frame/18 padded SRAM macros and central arithmetic band as baseline. Prior standard-cell area11,277um2 is conservative input until this variant's gate synthesis measures the valid-only implementation. Clock spread/timing/placement and data pin wire lengths await gate. Existing safety packet applies except item3 is FIXED structurally / awaiting measured max-load witness. Reset raw input drives32 wrapper copies, then each replica distributes only local registered reset consumers. Data cycles and compiler schedule charge0; provisional die-outline charge remains+69.215mm2 before real DIE refit.

Full25-leg exact matrix with safe reset defines running on fleet/Verilator5.050. Critical gate/review only; NO REVIEW.json or submit. Helpers tools/ref_tile, closure_loop and common_flow reset splitting are origin/main overlays and must not be committed as lane changes.

## SAFE-DESIGN checklist (LH-P3UNITS 10-19, before regate r2)
Gates 080811 (baseline) and 081811 (this kit) FAILED MECHANICALLY at 3_3_place_gp: `setRegionType FENCE` is not an OpenDB type ("Unknown region type"); no placement/CTS/GRT result exists, so this is not a failed route. Fix: EXCLUSIVE region (= DEF FENCE) + dbGroup membership, and the band widened to the FULL core width (2.16-429.84 x 183.6-248.4, 27.7k um2).
1 Pins: PASS - every data input/output registered in the RTL wrapper (one flop each, scheduled); reset rst_n -> 32 kept rqv copies -> smerge kept rst_c/rst_e/rst_m = 2 registered stages.
2 Reach: PASS by construction - 432 square; farthest macro edge to band ~150 um, N/S pin flops to band <=185 um (<405). Measure at gate.
3 Fanout: FIXED - mapped reset families max 29 loads (p3_sram_safe/reset_proof); mapped DFFASRHQN 590 (baseline 7,390).
4 Depth: inherited LAT-pipelined fp adders (ALAT 7); TT setup measured at gate.
5 Storage: FIXED - 36,864 shift flops -> 18 x 1R1W 128x256 SRAM macros + addressed metadata ring; remaining 18.5k flops are pin/pipeline registers (no runtime-indexed flop arrays).
6 Floorplan: macros on the 43.2 lattice (18, halo 5.4 on pin faces); one full-width central std band (fixed here); 432x432 aspect 1:1; std ~10.6k um2 (synth chip 84,364 - macros 73.7k) -> band util ~38%, whole-core fill 0.466. Outline is macro-driven.
7 Clock: single E-face root, tile 432 um; pin-flop spread <=80 TT+FF to be measured at gate; io hold budget die (OT_BH_*), io_hold_margin per kit defaults.
8 Schedule: PASS - static, 0 added cycles/II; reset copies add no edge.
Critical HBM tile: gate + PNG packet only, NO REVIEW.json / submit.
