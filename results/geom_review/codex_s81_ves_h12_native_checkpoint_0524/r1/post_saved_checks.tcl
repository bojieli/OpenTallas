source /work/clk_freeze.tcl
source /work/native_pg_binding.tcl
read_db $::env(VES_SAVED_ODB)
set b [ord::get_db_block]
set report [ot_pg_audit_snapshot $b /work/saved_GRT_PG.json]
if {[dict get $report failure_count]} {error VES_SAVED_PG_FAILURE}
ot_clk_dump /work/post_wire.tsv saved_GRT $::env(RESULTS_DIR)/clk_freeze_nets.txt
