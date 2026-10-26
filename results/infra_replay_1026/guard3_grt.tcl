read_db /work/guard3_combined.odb
write_db /work/guard3_before.odb
write_def /work/guard3_before.def
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -allow_congestion -guide_file /work/guard3_signals.guide
write_db /work/guard3_after.odb
write_def /work/guard3_after.def
exit
