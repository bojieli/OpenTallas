# S81 station t6 writer START reset

The a13 global-route TT setup gate measured −207.19 ps at 833 ps. During setup repair, the worst endpoint was the D pin of the ft3 FSTART face flop, from −305.04 ps before repair to −207.10 ps in its last iteration. The historical FF report shows a launch from reset relay u_rrl_56, through the ft3 reset AND input B, to that same register. The mapped FF report places 23 buffers between the reset launch QN and AND input B. This leg consumes 764.50 ps of the 829.58 ps QN-to-D path in that report. Source-to-face-pin Manhattan distance is 1,805.28 µm. Missing route-to-pin warnings remained in the final TT global-route estimate. The retained pre-repair GRT database is the comparator for an independent read of the launch, data input and reset input in the TT scene.

Four declarations in clock.landing_local_resets put one kept flip-flop near each FSTART output. The a13 generator resolves all four at the existing reset depth of six. The same clock and FSTART data drive all original face registers. The frozen outline is 1,442.88 × 1,278.72 µm. Inspection of the rendered source, copy and pin locations, and all ±2.16 µm placement boxes, found all four proposed boxes clear of the declared landing groups.

| Writer | Historical reset source to pin, µm | Depth-five raw to new copy, µm | New copy to pin, µm |
|---|---:|---:|---:|
| ft0 | 1,045.92 | 237.853 | 22.958 |
| ft1 | 804.896 | 26.909 | 24.016 |
| ft2 | 1,665.312 | 13.005 | 34.850 |
| ft3 | 1,805.280 | 149.139 | 34.904 |

The four-output miter uses the exact emitted baseline and candidate instances, including every reset ancestor up to the common raw root. Yosys temporal induction proves equality after seven edges from arbitrary power-on state, for arbitrary START data and reset assertions on every edge. Driving ft3 directly from its depth-five predecessor produces a counterexample. Added state is four one-bit flip-flops. Added FSTART, reset and data latency is zero cycles.

The J5 R4 plan has the same four face pins and outline, and an eight-stage reset tree. Its donor must use a depth-seven raw selected from the regenerated RTL. The a13 review and equivalence apply to the a13 candidate. Candidate physical timing remains open.
