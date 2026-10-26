read_db /work/target.odb
read_def -incremental /work/source.def
write_db /work/combined_before.odb
write_def /work/combined_before.def
set_routing_layers -signal M1-M3 -clock M1-M3
set_global_routing_layer_adjustment * 0.0
global_route -congestion_iterations 50 -allow_congestion -guide_file /work/signals.guide
write_db /work/combined_after.odb
write_def /work/combined_after.def
exit
