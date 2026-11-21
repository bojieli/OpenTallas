# QC V2 CB post-place failure review, 2026-11-21

Reviewed both exact retained images at each item’s geom/auto_geom.png. The epyc7 cbn_q00__cldbcda913 placement has the terminal n_b latch alongside the responding core pin. The detailed report measures 1.41 ps on the data wire and shows ideal −568.10 ps core source latency. PASS-COND for private CTS-only read of the retained placement. Retain the original failed stop. No detail-route verdict.

For epyc8 cbn_q11__cl49ae4555 the real latch and two inserted output buffers all sit west of u_t32. The data path briefly travels roughly 60 µm south and back. The printed 821.3 µm hop uses the macro origin instead of the terminal pin. The approximately 118 ps data-buffer and wire penalty is real. Hold routing until the output chain is seated locally and the corrected placement is viewed.

Viewed epyc2 fam-qc-cb-r2/v2_cf0b_outline/placed_review.png for cf0b12a5e785. Latch Q and actual n_b[372] terminal sit 3.5 µm apart. Exact reloaded STA reproduces −659.86 ps and 1.49 ps data wire, versus ideal launch −24.80 ps, ideal capture −1122.10 ps, and −303.93 ps macro tree. PASS-COND for CTS-only measurement on the retained placement.

Reviewed exact epyc7 V2 cbf_q00_s2 placed geom/auto_geom.png. Hold any new route of this shape. The internal V1-like geometry sends 516-bit BC output/receive chains around the corner with sampled 687 µm bc_o01 and 697 µm bc_i10 reaches. Hundreds of individual paths exceed the cycle budget. The tap-region concentration corroborates the long legs. Paired sender/receiver siting is the next physical correction.
