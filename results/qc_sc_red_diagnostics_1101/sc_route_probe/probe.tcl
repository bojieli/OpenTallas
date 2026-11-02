# One reviewed route-only capacity diagnostic from the honest native PLACE.
# Native Lib/unchanged SDC are loaded only for clock classification; no timing analysis, CTS, repair, placement or DRT.
source /work/native_clock_preflight.tcl
if {[info exists ::env(SC_CLASSIFICATION_ONLY)] && $::env(SC_CLASSIFICATION_ONLY) eq "1"} {exit}
source /work/sc_guard.tcl
source /work/pg_connect.tcl
check_placement -verbose
ot_pg_require_bound sc_probe_pre
set pre_cells [sc_cells];set pre_inc [sc_inc];set pre_terms [sc_terms];set pre_nets [sc_nets]
set clocks 0
foreach n [[ord::get_db_block] getNets] {
 if {[$n getSigType] eq "CLOCK"} {incr clocks;if {[$n isSpecial]} {error "SC_PROBE_EXCLUDED_SPECIAL_CLOCK [$n getName]"}}
}
if {$clocks!=2390} {error "SC_PROBE_CLOCK_NET_CENSUS $clocks !=2390"}
# Native asap7 factory setting: signal ceilingM5, clock minimumM4, capacity adjustment0.25.
set_routing_layers -signal M2-M5
set_routing_layers -clock M4-M5
set_global_routing_layer_adjustment M2-M5 0.25
puts "SC_ROUTE_ONLY_DECK signal=M2-M5 clock=M4-M5 adjustment=0.25 iterations=50 clocks=$clocks no_allow_congestion no_timing"
try {
 global_route -congestion_iterations 50 -congestion_report_file /work/sc_probe_congestion.rpt -verbose
 write_guides /work/sc_probe.guide
 write_db /work/sc_route_probe_retained.odb
 if {[sc_cells] ne $pre_cells || [sc_inc] ne $pre_inc || [sc_terms] ne $pre_terms || [sc_nets] ne $pre_nets} {error SC_PROBE_SOURCE_OR_POSE_CHANGED}
 puts "SC_ROUTE_ONLY_SOURCE_GUARD_PASS all_cell_masters_poses_flags_all_connectivity_public_pins"
 source /work/clock_guide_layers.tcl
 source /work/coverage.tcl
 write_db /work/sc_route_probe.odb
 puts "SC_ROUTE_ONLY_COMPLETE full_CLOCK_SIGNAL50 no_CTS_STA_DRT_or_closure_credit"
} on error {msg opts} {
 catch {write_guides /work/sc_probe_failed.guide}
 catch {write_db /work/sc_probe_failed.odb}
 return -options $opts $msg
}
