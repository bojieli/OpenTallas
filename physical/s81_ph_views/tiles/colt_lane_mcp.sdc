# CLAUDE S81-PH dsfd_colt_lane r4: the lane FIFO (ot_s81ph_colt_fifo) reads its SRAM at II 2 and captures rd_out two
# edges after the read (rq_r enabled by f2; no read is issued in between, so rd_out holds over both periods).  Design
# intent multicycle through the macro data outputs only: setup 2, hold 1 (hold still checked at the launch edge).
set ot_mo [get_pins -quiet -of_objects [get_cells -quiet -hierarchical -filter "ref_name == ot_sram_1r1w_256x256_m2_r2c2"] -filter "direction == output"]
if {[llength $ot_mo]} {
  set_multicycle_path -setup 2 -through $ot_mo
  set_multicycle_path -hold 1 -through $ot_mo
  puts "colt_lane_mcp: multicycle 2 through [llength $ot_mo] macro output pins"
} else { puts "colt_lane_mcp: no macro output pins found" }
