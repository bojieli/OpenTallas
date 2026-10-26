read_db /work/metal_free.odb
write_db /work/metal_free_before.odb
write_def /work/metal_free_before.def
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -allow_congestion -guide_file /work/metal_free_signals.guide
write_db /work/metal_free_after.odb
write_def /work/metal_free_after.def
exit
