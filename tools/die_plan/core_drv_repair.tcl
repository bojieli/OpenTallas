# GENERATED-COPY source: tools/die_plan/core_drv_repair.tcl (S81-CORES-1115, FABLE-PD-S81CORES-1915 1.2).
# Slew / cap repair on the global-route parasitics, once, before core_final_repair.tcl.  The core generator's POST_GLOBAL_ROUTE_TCL
# override (grt_post_core.tcl) replaced the legacy post_grt_drv.tcl, and SKIP_INCREMENTAL_REPAIR=1 removes the in-GRT repair_design,
# so without this file no repair_design runs after placement.  Self-gated: it runs only when the kit sets SKIP_INCREMENTAL_REPAIR=1
# (otherwise the in-GRT repair_design already ran) and OT_CORE_DRV_REPAIR is not 0.  A post-route ECO chain skips it
# (post_route_drv/post_grt_chain.py): the PRD hook already runs repair_design.  One incremental GRT session, no hold or setup repair here.
if {![info exists ::env(SKIP_INCREMENTAL_REPAIR)] || $::env(SKIP_INCREMENTAL_REPAIR) ne "1" ||
    ([info exists ::env(OT_CORE_DRV_REPAIR)] && $::env(OT_CORE_DRV_REPAIR) eq "0")} {
  puts "OT_CORE_DRV_REPAIR not run: in-GRT repair_design active or opted out"
  return
}
puts "OT_CORE_DRV_REPAIR begin: repair_design on GRT RC (SKIP_INCREMENTAL_REPAIR=1)"
estimate_parasitics -global_routing
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
puts "OT_CORE_DRV_REPAIR end"
