# L1 actual tail-buffer placement review

Verdict PASS-COND for one incremental DATA-only GRT50 trial, with exact reviewed placement digest b06d9229cfd99c205bec7f59c5eb6adf0602b3ca221a4843456be28a8e738ce4. CODEX personally viewed auto_geom.png and tail_zoom.png; independent geometry_disk reviewer concurs on the actual checkpoint.

The new BUFx6f is row legal at(106.758,190.350)..(107.298,190.620) in a macro-free column. Actual driver/buffer/capture center segments9.477/89.532um. Its area is0.1458um2; added state/mission/boot cycles0. Every original cell master, position, orientation, restored placement status and CLOCK connection is unchanged, enforced by the native placement script before PLACE_COMPLETE. No macro, halo, pin or PG channel changes.

Independent comparison to the original GEOM107 coupon finds all1010pin rows, macros/positions, outline,1935clockcells/39446rootedsinks unchanged. Actual pin-register p909.05/max81.91, r2r404.46/0over405, clockleaf53.14, cells-on-macro0 and blockedchannels0. Raw AUTO-GEOM FAIL from existing partial_face2 and custom-stage/templateNA remains in auto_geom.json; this scoped review does not overwrite it or authorize DRT/signoff.

GRT trial must reproduce the exact actual placement digest and preserve canonical CLOCK guide geometry. Native period833ps, latest OWNER12.24c setupuncertainty0/hold25 and ordinary10pskitrepair policy are unchanged; no margin waiver. Inherited uncertainty0 is the current policy, not a relaxation. Timing benefit is unmeasured. A result still requires routed current-tag signoff and own exactness gates before closure.

First GRT trial failed on missing private MM RESULTS_DIR creation; no timing result. That failure stays at epyc2 codex-qc-l1-tail-grt-2120/tail_grt.log. New separate trial codex-qc-l1-tail-grt2-2120 fixes only ordinary output-directory creation and preserves all inputs.
