source /work/sc_ff_master_preserve.tcl
# Original SC POST includes standard DATA repair and core_final_repair.
source /work/grt_post_core.tcl
source /work/grt_final_full.tcl
write_db /work/sc_native_repair_retained.odb
write_guides /work/sc_native_repair_retained.guide
ot_clk_freeze_assert sc_final_full_grt
ot_clk_dump $::env(RESULTS_DIR)/sc_clock_freeze/clk_freeze_post.tsv post $::env(RESULTS_DIR)/sc_clock_freeze/clk_freeze_nets.txt
exec python3 -I /work/clk_geom_diff.py $::env(RESULTS_DIR)/sc_clock_freeze/clk_freeze_pre.tsv $::env(RESULTS_DIR)/sc_clock_freeze/clk_freeze_post.tsv --json $::env(RESULTS_DIR)/sc_clock_freeze/clock_diff.json
if {[sc_terms] ne $::sc_repair_public_terms} {error SC_NATIVE_REPAIR_PUBLIC_PIN_MUTATION}
ot_pg_require_bound sc_final_full_grt
source /work/clock_guide_layers.tcl
source /work/coverage.tcl
