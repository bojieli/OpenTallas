# ot_hbm_accel_bulk_copy ENABLE=1 SRAM_RING=1 RING_MACRO=1: design-intent timing exception.
# Ring slot s lives in macro group s[0]; slots are taken strictly in order, so consecutive reads alternate
# groups and a group's read port latches a new address at most every other edge. Its rd_out therefore holds
# for two cycles, and the output-queue entry that captures it is enabled exactly two edges after the read
# (we<k> from rd_v2): a two-cycle setup path, hold checked at the launch edge.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_ring]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_ring]
