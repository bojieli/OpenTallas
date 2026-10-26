set PL /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PL/lef/asap7_tech_1x_201209.lef
read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /w/blk.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area {0 0 17.28 8.64} -core_area {0 0 17.28 8.64} -site asap7sc7p5t
foreach {l p} {M1 0.036 M2 0.036 M3 0.036 M4 0.048 M5 0.048 M6 0.064 M7 0.064} { make_tracks $l -x_offset [expr $p/2] -x_pitch $p -y_offset [expr $p/2] -y_pitch $p }
place_inst -name a -location {0 0} -status FIRM
place_inst -name b -location {8.64 0} -status FIRM
set_routing_layers -signal M2-M7
global_route -allow_congestion -verbose
write_db /w/t.odb
