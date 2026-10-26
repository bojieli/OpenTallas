read_db /work/reserved_combined.odb
write_db /work/reserved_before.odb
write_def /work/reserved_before.def
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -allow_congestion -guide_file /work/reserved_signals.guide
write_db /work/reserved_after.odb
write_def /work/reserved_after.def
exit
