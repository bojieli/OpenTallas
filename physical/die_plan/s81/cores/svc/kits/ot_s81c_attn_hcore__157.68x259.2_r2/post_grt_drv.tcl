# S81-HCORE r2: post-GRT DRV (slew/cap with the 40% estimation margin) + FF hold repair on the GRT parasitics, then legalise.
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20
repair_timing -hold -hold_margin 5 -max_buffer_percent 100
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
