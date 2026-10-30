PARKED read-only diagnostic; no candidate P&R, adoption or timing-gate credit.

Current FT query's normal GRT is still live on intel1. Its bounded TT repair reported −80.51 ps /348 endpoints; current incremental GRT has been quiet since08:20 but CPU-active. Independent read-only4_cts placement-RC report confirmed the same s0_x[153]→s1_m[1][28] path, −58.554 ps, with24 combinational levels/two serial31-bit compare-selects. This is predominantly logic depth, rather than a new macro/channel failure.

The24-cell genuine LVT coupon improves that endpoint to+20.259 ps (78.813 gain); it does not prove whole-query closure. Full max-tree fanin has6110 combinational cells/341D endpoints; converting it exposes the multiply product stage at−36.70 ps. The final measured scope adds48 product D endpoints, for389D endpoints/6519 DATA-only cells. Genuine LVT conversion gives whole-design placement-RC TT WNS+5.51 ps. A genuine SLVT comparison has the same global WNS+5.51, so it does not establish a reason to prefer SLVT. This margin may be consumed by GRT/RCX. No claim of833ps routed closure.

Actual target FF hold in the same4_cts placement-RC diagnostic changes+6.722→−0.596 ps under LVT; ordinary hold repair and full TT/FF gating are still required. All FF/clock masters and placements remain RVT/unchanged. Every replacement checks the genuine target LEF master, identical width/height and pin interface; source RTL/cycles are untouched. Only the four official AO/OA/SIMPLE/INVBUF LVT libraries are loaded; no fake FF assets.

OpenSTA default-activity power for6519 cells, same placement RC: RVT total5.304896mW/leakage0.476231uW; LVT total5.191493mW/leakage4.622385uW. Internal power increases0.259299mW, switching decreases0.376578mW, leakage increases4.146154uW. This is a measured same-input what-if, NOT workload or post-RCX power.

Remote logs/scripts: intel1:/srv/opentallas-scratch2/claude/codex-hbm-cores-1030/query_cts_diagnosis/{paths.log,lvt24.log,lvt_maxtree.log,lvt_arith.log,lvt_arith_ff.log,slvt_arith.log}. No ODB is written. Source4_cts and original kit are mounted read-only; output libraries/logs go to an independent /out, so the live setup watchdog cannot mistake them for its gate.

Diagnosed attempts retained: missing_LVT_LEF_SIGSEGV.log (STA library existed but physical master absent; corrected with genuine LVT LEF and footprint checks); async_input_boundary_count_FAIL.log (all_registers -data_pins includes RESET/SET; final candidate selects /D only). No failed result is called EQ or timing PASS.

Before any physical proposal, finish/collect the existing normal GRT, use its exact checkpoint and actual gate results, review the concrete physical mapping and power scope, run ordinary native proof/TTFF/DRV/PG gates, and retain the separate current-native outer-face +2/constant-output bridge hold. No new work was launched after Claude reset.
