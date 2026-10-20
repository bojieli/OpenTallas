# BTAB s3 structural clock successor

s2b failed TT/FF pin-flop spread109.4/97.2 despite mappedfanoutPASS, TTsetup+158.5/hold+62.2 and GRT0. The actual density PNG splits the register mass between N output captures and W/central select copies, while the default clock enters the far N-E corner.

s3 gives all320 registers a single explicit full-width N band (with legal rows clear of macro halos), splits bt_q into two128-bit ports around a centred N clock, and uses the symmetric insertion-aware clock spine. It retains the exact safe BTAB electrical datapath, four SRAMs, all16 kept select copies and both read edges. Added steady-state/reset/warmup cycles0; modelstorage16KiB/read32Bperedge/write128Bperedge unchanged. Parent must map {bt_qh,bt_ql} explicitly after closure.

Checklist beforegate: registeredinputs/outputflops PASS; reset N/A(no reset state); native32 PASS on exact wrapper ASAP7 mapping (maximum16 immediate loads, independent transitive census zero>32); storage PASS4SRAM/320flops; plannedreach<=405(registered N band to macro readfaces<386um, inputwriteface to macrofaces<320um); macro43.2grid/45.3um full-width channel PASS; pinfaces<=6/um; aspect1.4 PASS; newclock centre-fed symmetric spine plus all-register band, spreadmeasuredgate owed; staticzeroedge schedule PASS. No geometry tuning or resubmission of failed s2b.

Fleet Verilator5.050 split-port exact bench PASS12000cycles/nonzero11863; real bank mutantFAIL137. Synthesis retains320FF+fourSRAMs+16kept select identities; no storage or timing edge changes.
