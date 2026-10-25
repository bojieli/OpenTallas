# PATH-S81/HCORE swr 10-25: post-GRT DRV only.  FF hold is repaired in its own one-scene OpenROAD process after CTS
# (repair_ff.tcl, run_swr.sh); the former mixed tc+bc `repair_timing -hold` here was the hcore_eh1 stall (pads the FF corner
# against the TT bound, 6k pin-reg endpoints, hours).  Setup is checked independently at TT after the FF repair.
global_route -start_incremental
set_max_fanout 16 [current_design]
set_max_transition 200 [current_design]
repair_design -slew_margin 20 -cap_margin 20
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
