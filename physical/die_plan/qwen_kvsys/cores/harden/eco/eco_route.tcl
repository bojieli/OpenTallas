# KV-CORES 10-24: warm post-route ECO of a routed KV hard core (ORFS POST_GLOBAL_ROUTE_TCL hook of a do-route that starts
# from the core's own 5_2_route.odb, copied in as 4_cts.odb; 6_final.spef in RESULTS_DIR = that route's RCX).
# Derived from ELEM-QK recipe b (tools/elem_qk/hold_eco/hold_route.tcl on claude/elem-qk-1024: FF-only hold margin 3
# left -1.6..+0.09 ps residual on the 285 heads), plus the DRV fix the 216 heads need: the TT/FF max-slew violators
# are all placement-buffer nets with fanout 55-174 (ASAP7 liberty has no max_fanout) whose routed RC gives 320-507 ps
# at the far loads while the driver slew is ~60 ps (probe tools/kv_cores/slew_nets.tcl).  Steps (env knobs):
#   OT_MAX_FANOUT   set_max_fanout on the design, then repair_design splits the high-fanout nets      (0 = skip)
#   OT_SLEW_MARGIN  repair_design -slew_margin / -cap_margin (percent)
#   OT_SETUP_MARGIN repair_timing -setup -setup_margin (ps; "" = skip; MCMM tc+bc variants)
#   OT_HOLD_MARGIN  repair_timing -hold -hold_margin (ps), OT_HOLD_ALLOW_SETUP, OT_HOLD_MAXBUF
# No RTL / cycle / clock-tree / SDC change; the verdict is tools/die_plan/signoff.py TT setup / FF hold on the re-routed DB.
read_spef $::env(RESULTS_DIR)/6_final.spef
global_route -start_incremental
if {$::env(OT_MAX_FANOUT) > 0} {
  set_max_fanout $::env(OT_MAX_FANOUT) [current_design]
}
puts "KVCORES_ECO repair_design slew_margin $::env(OT_SLEW_MARGIN) max_fanout $::env(OT_MAX_FANOUT)"
repair_design -slew_margin $::env(OT_SLEW_MARGIN) -cap_margin $::env(OT_SLEW_MARGIN)
if {$::env(OT_SETUP_MARGIN) ne ""} {
  puts "KVCORES_ECO repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN)"
  repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp
}
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
puts "KVCORES_ECO repair_timing $args"
repair_timing {*}$args
detailed_placement
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
