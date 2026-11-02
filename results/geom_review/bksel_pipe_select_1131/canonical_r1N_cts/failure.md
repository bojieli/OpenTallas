# Immutable R1N packaging FAIL

Collected 2026-11-01 16:10:20 PST. CTS exit2 at16:03:05 PST, epyc2 unitoth-ubuntu-2013928-1793577498. The canonical MM runtime patch succeeded, but the GRT-only input snapshot lacked the configured POST_CTS_TCL file. Exact native failure:

    source /work/cts_post.tcl
    Error: cts.tcl, 87 couldn't read file "/work/cts_post.tcl": no such file or directory
    make[1]: *** [Makefile:548: do-4_1_cts] Error 1
    make: *** [Makefile:548: /work/run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r1_1131/base/4_1_cts.odb] Error 2

Native elapsed4:42.23, peak2025384KB. No valid completed CTS checkpoint or qualification. No active overlay was used; input and failure remain preserved. Source formal EQ and exact corrected placement remain valid. See canonical_r1Q_prepared for the complete original-kit input replacement, prepared only.
