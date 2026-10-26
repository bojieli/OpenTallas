read_db /work/status_combined.odb
write_db /work/status_before.odb
write_def /work/status_before.def
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -allow_congestion -guide_file /work/status_signals.guide
write_db /work/status_after.odb
write_def /work/status_after.def
exit
