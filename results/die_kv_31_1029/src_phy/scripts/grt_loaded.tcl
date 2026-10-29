# DIE-KV-31-SRC: loaded KV die GRT0 incl clock on the PG-accessed actual source (METHODOLOGY 12.4a: judged at >=50 it).
# Layers/adjustments = the source's own die_trial settings (native_source/source.tcl): signal M4-M7, clock M8-M9.
set t0 [clock seconds]
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_db /n/access/access.odb
create_clock -name dck -period 833.333 [get_ports root]
puts "OT_T read [expr {[clock seconds]-$t0}]"
set_routing_layers -signal M4-M7 -clock M8-M9
set_global_routing_layer_adjustment M4 0.75
set_global_routing_layer_adjustment M5 0.75
set_global_routing_layer_adjustment M6 0.75
set_global_routing_layer_adjustment M7 0
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /n/grt/congestion.rpt
puts "OT_T grt [expr {[clock seconds]-$t0}]"
if {[catch {grt::report_layer_wire_lengths} e]} { puts "OT_NO_LAYER_WL $e" }
write_guides /n/grt/route.guide
write_db /n/grt/grt.odb
puts "OT_T written [expr {[clock seconds]-$t0}]"
puts OT_DONE
