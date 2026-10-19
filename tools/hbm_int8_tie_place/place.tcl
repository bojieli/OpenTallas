set p /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $p/lef/asap7_tech_1x_201209.lef
read_lef $p/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach lib [glob $p/lib/NLDM/*RVT_TT*.lib*] { read_liberty $lib }
read_verilog /work/netlist.v
link_design ot_smh_int8_tile_safe
initialize_floorplan -die_area {0 0 237.6 129.6} -core_area {2.16 2.16 235.44 127.44} -site asap7sc7p5t
source $p/openRoad/make_tracks.tcl
set_io_pin_constraint -group -region top:2-3 -pin_names {i_v}
set_io_pin_constraint -group -region top:3-8 -pin_names {i_tag[*]}
set_io_pin_constraint -group -region top:10-234 -pin_names {i_codes[*]}
set_io_pin_constraint -group -region bottom:2-3 -pin_names {o_v}
set_io_pin_constraint -group -region bottom:3-8 -pin_names {o_tag[*]}
set_io_pin_constraint -group -region bottom:17-234 -pin_names {o_data[*]}
set_io_pin_constraint -group -region bottom:8-15.5 -pin_names {o_sel[*]}
set_io_pin_constraint -region left:62.8-64.3 -pin_names {clk}
set_io_pin_constraint -region left:65.3-66.8 -pin_names {rst_n}
place_pins -hor_layers M4 -ver_layers M5 -min_distance 4 -min_distance_in_tracks
create_clock -name core_clk -period 0.77 [get_ports clk]
source $p/setRC.tcl
global_placement -density 0.50 -skip_io
detailed_placement
check_placement -verbose
write_db /work/before.odb
source /work/die_constant_cells.tcl
check_placement -verbose
write_db /work/after_ties.odb
source /work/pdn.tcl
pdngen
check_power_grid -net VDD
check_power_grid -net VSS
write_db /work/placed.odb
write_def /work/placed.def
write_verilog /work/placed.v
puts "INT8_TIE_PLACEMENT_FINISHED_NO_CTS_NO_ROUTE"
