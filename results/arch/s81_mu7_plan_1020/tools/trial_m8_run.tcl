# S81-MU7PLAN 10-20 trial GRT: mu5k post-repeater grt.odb (same netlist + placement), ONLY change = M8 opened as a die signal layer.
read_db /in/out/grt.odb
set_routing_layers -signal M2-M8 -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M8 0.20
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {[clock seconds]-$t0}]"
write_db /work/out/grt.odb
puts OT_DONE
