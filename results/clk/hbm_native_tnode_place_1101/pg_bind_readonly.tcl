read_db /work/run/results/asap7/hbc_ot_hnx_fused_tnode/base/3_place.odb
source /work/pg_connect.tcl
set before 0
set block [ord::get_db_block]
foreach inst [$block getInsts] {incr before [ot_pg_open_terms $inst]}
puts "OT_RAW_PG_OPEN_TERMS $before"
set rebound [ot_pg_connect_all read_only_pre_cts]
set total [ot_pg_require_bound read_only_pre_cts]
puts "OT_READONLY_PG_BIND_PASS before=$before total=$total protected_rebound=$rebound"
