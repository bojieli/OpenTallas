set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] { read_liberty $f }
read_db /work/mesh_before.odb
read_sdc /work/mesh.sdc
set_routing_layers -signal M1-M7 -clock M1-M7
set_global_routing_layer_adjustment * 0.0
global_route -verbose -congestion_iterations 50 -guide_file /work/clock_stubs.guide
write_db /work/mesh_grt.odb
write_def /work/mesh_grt.def
detailed_route -output_drc /work/drc.rpt -output_maze /work/maze.log -verbose 1
write_db /work/mesh_routed.odb
write_def /work/mesh_routed.def
exit
