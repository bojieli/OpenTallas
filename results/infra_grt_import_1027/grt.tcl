set t0 [clock seconds]
read_db /out/combined_infra.odb
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -allow_congestion -guide_file /out/signals.guide
write_db /out/routed_signal.odb
