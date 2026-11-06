read_db /out/clock_leaf_fixture.odb
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment M2-M5 0.3
global_route -guide_file /out/clock_component.guide -verbose
write_db /out/clock_component_grt.odb
detailed_route -output_drc /out/clock_component.drc -droute_end_iter 10 -verbose 1
write_db /out/clock_component_routed.odb
