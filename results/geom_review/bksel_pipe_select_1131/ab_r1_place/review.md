# Actual corrected A+B R1 placement review

Personally viewed auto_geom.png ; review recorded 2026-11-01 13:09:38 PST. Verdict FAIL; no CTS or routing. Source and fresh synthesis receipts are in results/rtl/bksel_pipe_select_1131/fresh_synth. Whole-kit native equivalence is still pending at this review.

The frozen 388.8 x 172.8 um parent outline matches exactly (aspect 2.25 remains an AUTO failure). Actual 140,354 standard cells and 25,659 flops occupy 26.14% of macro-free area; 28.02% of density bins are nearly empty. The image shows dense north/south face bands, a broad internal logic island and an east cluster, with no macros. All signal pins are registered: p90 pin-to-register 9.09 um, max32.93 um; pin density6.0 per-layer/face.

Genuine reach failure: reset source u_c.rst_s[1] bounds x381.618..383.022/y107.190..107.460, centre(382.320,107.325), to face register u_c.sq[15] bounds x4.428..5.832/y5.130..5.400, centre(5.130,5.265), Manhattan479.25um. There are680 captures over405um. This needs a legitimate reset-locality fix and preserved reset/cycle/face contract before advancing.

Vertical demand estimate0.64 at(240,72.5) exceeds0.6 review threshold, below hard1.0; actual GRT was deliberately NOT RUN. The channel estimate failure remains, with no routing waiver. Clock reach511.79um is pre-CTS information because0fixedclockcells; all25,659 sinks are rooted. No CTS geometry or routed timing claim is made.
