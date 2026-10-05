# ot_rom_oneshot_die_f12 FIFO_IMPL=2: design-intent timing exception (the closed bulk-copy RING_MACRO=1 pattern).
# Storage word w lives in bank w[0]; reads leave strictly in order, so consecutive reads alternate banks and a
# bank latches a new read address at most every other edge. Its rd_out therefore holds for two cycles, and the
# output-queue entry that captures it is written exactly two edges after the read (fill_v = rd_v2): a two-cycle
# setup path from the macro, hold checked at the launch edge.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_ring]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_ring]
