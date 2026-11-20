# J5 R4 station t6 component donor

The exact original J5 R4 plan passed elaboration and stopped during whole-die bind at bk_sel. A separate station-only call to the R4 landing generator reproduced the same interface defect on the ft0 forwarded clock, whose declared source clk_t5 was missing from the interface. Restoring the station's forwarded_clock_only_inputs flag recovered the station's existing forwarded clock ports. The pending full-die repair owns the flag across the affected types.

The station reference uses the 13 feedthroughs from a previously bound station. Reapplying the historical J6 generator to the recovered native body reproduces its complete token sequence. The R4 bound-latency record verifies every feedthrough's active width, and the R4 FT plan verifies every local stage count. The R4 reset solver and the declared physical collector tree agree on all 188 relay identities. The R4 generator then emits the complete landing RTL on its native depth-eight tree. Its candidate differs only in four additional kept one-bit flops and their four FSTART synchronous reset connections. No parent interface clock, reset date, FSTART date or feedthrough latency changes between this R4 reference and candidate.

| Writer | Depth-seven source | Source to new copy, µm | Copy to pin, µm | Clearance to nearest declared FT bit cell, µm |
|---|---|---:|---:|---:|
| ft0 | rst_rl_81 | 166.163 | 22.958 | 9.936 |
| ft1 | rst_rl_148 | 26.909 | 24.016 | 11.988 |
| ft2 | rst_rl_185 | 106.306 | 34.850 | 20.250 |
| ft3 | rst_rl_185 | 55.208 | 34.904 | 19.116 |

The regenerated floorplan image was viewed. All four emitted local-copy boxes are inside the 1,442.88 × 1,278.72 µm outline and clear the declared ring and collector boxes and the 11,028 explicitly sited FT bit cells. The candidate preserves the 38 existing clock taps. The lines between sites represent connections and are priced using Manhattan distance.

Yosys temporal induction on the four real writer/reset cones passes from arbitrary initial state after nine edges, for unconstrained data and reset on every edge. Replacing the eighth-stage copy at ft3 by its seventh-stage input fails the same comparison and produces the saved counterexample. Both complete station modules elaborate in Verilator with the same existing unused optional rst_xn pin warning. Icarus rejects existing elaboration-time $error syntax in the common library on both inputs.

This is a scoped source and geometry result. The private composition is on epyc2 under d8j/j5_intake/station_t6_start/r4/plan_j5_r4_station_t6_private.json. Its SHA256 begins 679d950fb6bc. The strict forward-ABI continuation checks the complete newly bound station against the scoped reference before attaching the four rows to that full plan. An actual candidate placement and its TT and FF timing remain unmeasured.
