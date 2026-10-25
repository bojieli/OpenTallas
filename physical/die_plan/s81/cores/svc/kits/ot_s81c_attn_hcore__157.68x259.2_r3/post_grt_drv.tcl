# S81-HCORE r3: post-GRT DRV + FF hold + TT setup repair on the GRT parasitics, then legalise.
# r2 signoff (RCX): 10 TT / 12 FF slew violators at 340-357 ps on two 13-15-fanout buffer nets whose GRT-estimated slew
# passed the 40% margin, output-flop FF hold -2.95, TT setup -1.30 (ld_grp write-enable).  Flow-only targets below the
# liberty limit (the signoff SDC is the kit constraint.sdc, unchanged): max transition 200 ps, fanout 16.
global_route -start_incremental
set_max_fanout 16 [current_design]
set_max_transition 200 [current_design]
repair_design -slew_margin 20 -cap_margin 20
repair_timing -hold -hold_margin 25 -max_buffer_percent 100
repair_timing -setup -setup_margin 15 -repair_tns 100
repair_design -slew_margin 20 -cap_margin 20
repair_timing -hold -hold_margin 25 -max_buffer_percent 100
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
