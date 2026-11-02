# Native BFQG source model review

LOOKed the rendered current E macro and literal native port plan before any physical launch. The image shows the actual six-left/two-right macro arrangement, twenty native clock inputs, and the existing reset input. It is a reference source plan; no placed standard cells or clock tree are present.

Source canary: GEN, LINT, PREFLIGHT, synthesis, face_guard (1319/1319), and port_bind (zero missing/extra) all pass. Official equivalence is 8650/8650 with zero differences or undecided points and requested/used reset edges four. Actual synthesis has 3890 FFs and eight SRAMs. The source pipeline and resource model are in results/hbm_bfqg_native_source_1520/native_component_model_prep.json; the actual receipt is adjacent.

PHYSICAL REVIEW HOLD: the existing native data stages and twenty clock ownership domains require a concrete placement/tree model and review before PNR. Historical wrapped four-plus-four placement, global-route and timing coupons remain diagnostics and confer no current native physical or timing qualification. No native PLACE, CTS, GRT, DRT, token or throughput result is claimed.
