# QC native START source candidate

The old nearest-GLUE capture graph did not match RTL `.clk(clk)`. Native313-clock reprice preserves the measured actual26 data hull (only rounded wander expanded conservatively) and exposes192 physical failures across462-um hard-core walls, maximum658.622um. All3194 START phases remain clean; no failed graph was emitted for adoption.

A direct-midleg siting attempt failed the actual hard-core halo and remains FAIL. Two explicit neighbor relays around each wall give384 aliases,3266 virtual stages and3578 physical START hops. The original44590 clock cells, nets and sites remain identical. Provisional phase plan:3578/3578 clean;2525 data crossings D4, margins107.4/335.4ps. Maximum341-cycle origin is relative to root START, **not absolute boot**; rootSETTLE64 adds65 local clocks and actual native reset entry still needs measured phase.

The source7502720af bounded reset-wave emitter replaces the global reset star. Root alone takes timed local reset, with explicit root alias; every child receives ordinary registered reset from its START parent. Two-dimensional FF row reservations keep complete emitted envelopes at403.92um maximum/0over405.

The earlier66b virtual-root source had undriven `st_b0_rraw`: Yosys optimized all9546 added reset FF away while final check passed. Its22365 declared FF mapped to12819, so it is HELD/FAIL. Correct750 source maps48259 cells =22365FF+25894comb,7805.05308um2. Exact per-stage FF and reset-role counts pass the current guarded collector. No physical qualification is borrowed from the bad source.

Actual old-global-reset mapped diagnostic placement (not adoption):29167 cells,12819FF+16348comb,all-cell registered reach400.05um. Fresh fixed-reset placement and island union are owned by the mapped provider importer lane. Combined44590 clock +48259 provider cells need185698 PG contacts; the old89180 clock-only plan is insufficient.

Canonical run root: intel2:/srv/opentallas-scratch2/claude/codex-qc-start-native-0251. `reset_wave2/emitted` is fixed source; `reset_wave2/synth/provider_cells.json` is the guarded mapped inventory. Native reset infrastructure is separate source910c1e5bd. It discovers actual local root source `sl_E0_fw.rst_o_0`171.804um away, source-part release15clocks. Actual root timing/phase and absolute boot are NOT RUN.

No P&R, final clock/load phase, die PG, SIGNED view or release adoption is claimed.
