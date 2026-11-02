Independent HEAD Turn5 real-clock profile source/context review

Reviewed source43e49c51f11ab29e9ca91ad2aad3fb5b2ee499f9 on codex/postcts-partition-binding-1102, owned by qc_nl_prefix/FLOW. Static CONCUR for one separately scoped read-only paired A/B diagnostic; no shared edit, native experiment or dispatch by this reviewer.

Exact retained Turn5 ODB SHA89b914844f875f418cb1578b29634d5221b74b79206bbb269f5fb7c3ee2f5f3c. Readset /srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn. constraint.sdc declares five source-bearing real clocks: clk on fourteen ports, fclk_in_d1_i, fclk_in_u1_i, generated fclk_out_d1_o and fclk_out_u1_o; vclk is the sole source-less reference. Existing consumer propagated only clk.

Exact query_TT.log lines963–997: cland_fstart_in_u1_i, launched against ideal vclk450 plus126.6 external input delay, reaches u_cland_u1_i/u_ring.s_d[1][10] D at1165.65ps. Capture fclk_in_u1_i is incorrectly ideal0, giving833−7.51=825.49ps required and−340.16ps slack. This path is not the SDC416.5ps clk↔fclk max-delay relation; no half-cycle constraint change follows.

The candidate source-bearing predicate matches existing repair_ff.tcl. Flag OT_POSTCTS_REAL_CLOCK_PROFILE absent/0 preserves legacy primary-only propagation;1 includes all declared real clocks, and invalid values refuse. The unique source-less virtual reference remains ideal and its corner frame unchanged. Pin-register measurement intentionally remains clk-family-only; it must not absorb forwarded-clock arrivals into that insertion budget. Exact Lib/SDC/RC, uncertainty0/25, golden frame, tolerance profile OFF and band policy remain unchanged. Canonical signoff.py already propagates all clocks.

The paired diagnostic must preserve old results, log actual clock profile and propagated capture paths, use fresh global RC, and retain every positive or negative TT/FF outcome. Real capture latency can move both setup and hold results; no predicted timing pass, rejudge, source adoption, route, repair, CTS or signoff credit is inferred. Tests are source/Tcl tests only; this review creates no native qualification.
