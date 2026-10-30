# QC COLLFT core_forest acceptance (DIE-QC-48, 2026-10-30)

Consumer-side acceptance of FLOW-9 `claude/flow-9-forest-1030@8bc5475ee9f` on the real QC coll_ft__cla4a25d77
forest fixture (Codex 515014cc720 `results/collft_clock_architecture_0336`: forest_fixture.json,
tree_packed_actual_pins.json.gz, packed_full_models.json.gz).

    python3 collft_accept.py <tools/die_plan> <fixture dir> <work dir>   # 11 cases, collft_accept.json
    python3 ident.py <tools/die_plan> <fixture dir>                      # default-off byte identity (single core_tree)

Result on the tip: OVERALL PASS 11/11 (RCLK8: 8 roots, 4948 cells, 9428 sinks, 8 begin/finish; ALL15: 15 roots,
8436 cells, 18501 sinks; 9 fail-closed mutants refused with the expected reason). On main: core_forest is ignored
(KeyError), as expected. ident.py: 15/15 per-root single core_tree emit_tcl + emit_cts_tcl + compiled plan JSON
identical main vs tip.

HARNESS-ONLY fills (the QC graph regeneration must supply these itself): per-root name prefix f<k>_; sink spelling
`<inst>/CLK` (the fixture lists instance names only, which ot_ci_tree_sink would split at the last '/');
pin_latency_ps per leaf + model_qualification (from packed_full_models leaf_means, band/window policy info per 12.3a).
