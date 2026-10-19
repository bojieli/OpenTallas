read_liberty cells.lib
read_liberty zh_tt.lib
read_liberty recip_tt.lib
read_db global.odb
initialize_floorplan -die_area {0 0 734.4 540} -core_area {21.6 226.8 712.8 231.66} -site asap7sc7p5t
set_thread_count 8
detailed_placement
check_placement -verbose
write_db placed_cells.odb
exit
