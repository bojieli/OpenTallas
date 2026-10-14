read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/view.lef
read_verilog /work/pa.v
link_design pa_top
initialize_floorplan -die_area {0 0 666.144 248.832} -core_area {0 0 666.144 248.832} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
place_inst -name u0 -location {10.368 10.368} -orientation R0 -status FIRM
place_inst -name u1 -location {333.12 10.392} -orientation MX -status FIRM
place_inst -name u2 -location {10.4 124.416} -orientation MY -status FIRM
place_inst -name u3 -location {333.152 124.44} -orientation R180 -status FIRM
set_thread_count 4
set_routing_layers -signal M2-M7
if {[catch {pin_access -verbose 1} err]} { puts "OT_PA FAIL $err" } else { puts "OT_PA DONE" }
exit
