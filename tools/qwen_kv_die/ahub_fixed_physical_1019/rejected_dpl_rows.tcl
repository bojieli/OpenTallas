read_liberty cells.lib
read_liberty zh_tt.lib
read_liberty recip_tt.lib
read_db placement_input.odb
set_thread_count 8
global_placement -density 0.55 -skip_io -overflow 0.10
write_db global.odb
detailed_placement
check_placement -verbose
write_db placed_cells.odb
write_verilog placed.v
exit
