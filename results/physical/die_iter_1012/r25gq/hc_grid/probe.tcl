read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/hc_probe.lef
read_verilog /work/hc_grid_probe.v
link_design grid_probe
initialize_floorplan -die_area {0 0 32984.288 25980.528} -core_area {0 0 32984.288 25980.528} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /work/sta_stn/case/snap.tcl
set blk [ord::get_db_block]
set master [[$blk findInst hc0] getMaster]
foreach o {R0 MX MY R180} {puts "HC_RULE $o [ot_mts::rule $master $o]"}
ot_mts::place [$blk findInst hc0] 8563.920 11141.280 R0
ot_mts::place [$blk findInst hc1] 21293.264 11141.280 MY
ot_mts::place [$blk findInst hc2] 8563.920 13340.208 R0
ot_mts::place [$blk findInst hc3] 21293.264 13340.208 MY
ot_mts::assert_on_track -label hc_legal_orients
