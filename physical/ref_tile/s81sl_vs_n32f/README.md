# s81sl_vs_n32f: current VS SRAM/native32 candidate

Exact RTL source: `8f57521dc`; top `ot_s81sl_vs`; definitions `OT_S81SL_VS_SRAM` and `OT_S81SL_VS_FP_N32`; no parameter overrides. Outline 216.0 x 237.6 um. This collector has preserved the live r5 gate and has launched no replacement.

Source-bound receipts: `results/rtl/s81_vs_takeover2_1021/source_binding.json`. All fourteen RTL files match the actual r5 bench snapshot and actual ORFS gate snapshot. Existing VS six-class positive has zero mismatches, MUT1 is caught with418 SW errors, and ENG reports4 partials/16 half-rows/zero mismatches with159/73-cycle dates.

SAFE review, carried forward from ELEM-XFV/VS before the live gate, with current measured facts:

1. Pins: source capture/output registers and existing two-stage reset landing retained. Same-region direct paths retain their original contract; parent crossing/long-wire binding remains a parent obligation.
2. Reach: planned local macro/cell layout retained; actual routed reach/timing remains pending the current gate. No additional relay or edge is claimed.
3. Fanout: PASS on the actual ORFS gate mapped netlist, maximum32 dynamic loads, zero violations and zero Liberty-role errors. This supersedes the old proxy census qualification.
4. Depth: exact LAT6 arithmetic and command stages retained; physical setup/hold qualification remains pending the live gate and eventual route.
5. Storage: eight real32x128 SRAM banks hold the runtime-indexed h stash; the remaining bounded control/operand registers retain their existing function.
6. Floorplan: actual eight-macro MAIN/FALLBACK placement, lattice geometry, halos and channel plan retained. Gate geometry/resource checks and GRT are authoritative; no outline shrink or density override was introduced.
7. Clock: one local clock; existing0.03ns hold margins and constraints retained. Measured TT/FF pin spread and timing remain pending the live gate; no clock waiver is introduced.
8. Schedule: no new protocol or arithmetic edge; existing VS/ENG cyclewise goldens pass, including ENG159/73.

Physical status at receipt creation: RUNNING, not adopted and not CLOSED. Inspect the actual terminal gate result and PNGs before submission.

Terminal r5 gate: WARN with no FAIL, actual native32/0/0, trial GRT overflow0 (worst M2 usage41.79%), depth538.4ps/reach167.7um; measured pin-flop TT/FF spreads56.4/55.9ps. Placement-RC diagnostics: setup+21.7ps/hold+34.7ps, not routed signoff. Actual geometry2859pins, all track-accessible/no outside or missing rectangles. Synthesized std14475um2+macros8550um2; effective placeable utilization43%.

Both actual floorplan/density PNGs viewed: eight macros in2columns x4rows, no overlap, full standard-cell bands between/around macros; clock pin on SW face, geometry and density consistent with the captured gate. Existing clock-count/insertion and boundary-depth guidance remain explicit WARNs; no new waiver or constraint edit. Noncritical list check and prior failed-route count0 permit direct submission; no REVIEW.json is created.
