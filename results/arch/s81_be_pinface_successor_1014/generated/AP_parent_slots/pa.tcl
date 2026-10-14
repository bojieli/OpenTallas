read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/view.lef
read_verilog /work/pa.v
link_design pa_top
initialize_floorplan -die_area {0 0 1887.384 196.56} -core_area {0 0 1887.384 196.56} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
place_inst -name u0 -location {64.8 21.6} -orientation R0 -status FIRM
place_inst -name u1 -location {540.0 21.6} -orientation R0 -status FIRM
place_inst -name u2 -location {1015.1999999999999 21.6} -orientation R0 -status FIRM
place_inst -name u3 -location {1490.3999999999999 21.6} -orientation R0 -status FIRM
set_thread_count 4
set_routing_layers -signal M2-M7
if {[catch {pin_access -verbose 1} err]} { puts "OT_PA FAIL $err" } else { puts "OT_PA DONE" }
exit
