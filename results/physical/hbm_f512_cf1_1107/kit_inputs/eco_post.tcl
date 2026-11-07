source /work/kit_modes_eco.tcl
source /work/prd_hook.tcl
kit_modes_eco_done
source /work/prd_post_grt_chain.tcl
source /work/pg_connect.tcl
if {(![info exists ::env(OT_PG_STRICT)] || $::env(OT_PG_STRICT) ne "1") && [llength [[ord::get_db_block] getGlobalConnects]]} {ot_pg_connect_all post_route_drv}
ot_pg_require_bound post_route_drv
