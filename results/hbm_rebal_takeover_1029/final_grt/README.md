# HNX actual post-pad GRT: FAIL, no DRT

Same-synth original833ps TT/FF source/SDC/vclk250/202.5 and max4 data-only IO pad. GRT completed3781s, overflow0, antenna0, PG402332/open0. Actual37757 register captures: max387.75um, zeroover405, combinational loops0. Fresh canonical postcts_gate script loaded exact5TT and5FF libraries, selected /work/setRC_rcx.tcl and global-routing parasitics: TTsetup+18.89ps, FFhold−0.23ps. Insertion fixedboundary gate also FAIL: TTmean298.05vs250 (48.05 deviation), FFmean242.32vs202.5 (39.82), tolerance20. The gate process exits0 evenwhen its JSON verdict isFAIL; use the JSON.

The old bundled orfs_hold_mm RC restore sourced platformsetRC rather than selectedLAYER_PARASITICS_FILE. Its calibrated intermediate FF+0.002/0 was not final closure. Old log labels 'SS setup' are historical: OT_MM_SETUP_CORNER=tc and TC_LIB_FILES select actualTT. Fresh per-corner receipts remove this ambiguity.

Complete semantic clock traversal starts only actual sequential/macro clock-pin-tagged inputnets and follows buffer/clock drivers (flaggedclockinput only on multinput cells, never gate enable cones). All1968 clockcells, graph andsinkidentity unchanged, zeroambiguousdriver, but oneBUFx24 clockbuffer and30sinkflop bodies moved. ClockfreezeFAIL. Exactclockbuffer location delta and all31proposed restoration sites are recorded. Preserving masters/graph alone is insufficient.

Personal geometry view actual_grt.png: compact macrofree frame, original jv anchor reach387.75 maintained; no newmacro wall/sliver. FAILFORNEXTSTAGE because clockgeometry+FFhold+fixedinsertioncontract remain open. The31site restoration is a proposal only and does not solve systematic insertiondev48/39.82. No clockrebind/retime, no DRT, no sourceadoption. Parent coordinator owns nextreview.

Runtime intel2 /srv/opentallas-scratch2/claude/codex-hbm-rebal-0310/kit (5_1_grt.odb SHA1 779749e59107ec0a0de5...). Readonly geometry unit186952, authoritative timing unit202861. Full geometric TSVs retained in sibling local scratch final_grt; not committed.
