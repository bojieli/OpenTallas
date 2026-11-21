# QC V2 CB post-place failure review, 2026-11-21

Reviewed both exact retained images at each item’s geom/auto_geom.png. The epyc7 cbn_q00__cldbcda913 placement has the terminal n_b latch alongside the responding core pin. The detailed report measures 1.41 ps on the data wire and shows ideal −568.10 ps core source latency. PASS-COND for private CTS-only read of the retained placement. Retain the original failed stop. No detail-route verdict.

For epyc8 cbn_q11__cl49ae4555 the real latch and two inserted output buffers all sit west of u_t32. The data path briefly travels roughly 60 µm south and back. The printed 821.3 µm hop uses the macro origin instead of the terminal pin. The approximately 118 ps data-buffer and wire penalty is real. Hold routing until the output chain is seated locally and the corrected placement is viewed.
