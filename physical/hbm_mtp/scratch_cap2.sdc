# ot_gpu_scratch_service CAP2=1: design-intent timing exception. A read latches its address at edge 0; the
# port takes no new address until the response is consumed (ready = !pending && !pending2 && !done), so the
# macro's rd_out holds and rdata captures it at edge 2: a two-cycle setup path, hold checked at the launch edge.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_sram]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_sram]
