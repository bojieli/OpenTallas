set_thread_count 8
read_db /diag/shift.odb
read_guides /audit/results/asap7/opentallas_qfd_tt_scale_leaf_asap7_ref_qfd_tt_scale_leaf_fs4_0d82da4ab/base/route.guide
set_routing_layers -signal M2-M5
set_propagated_clock [all_clocks]
detailed_route -output_drc /diag/route.drc -output_maze /diag/maze.log -droute_end_iter 1 -verbose 1
write_db /diag/routed.odb
