# fc_bc: the bulk copy's ring read is a designed two-cycle path (oq5 RING_MACRO=1; rd_out registered at E1, oq* capture at E3);
# identical to front_c's hand SDC (tools/hbm_accel_smh_physical.py sdc_block ring=True) and ot_hbm_accel_bulk_copy_mc2.sdc
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_ring]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_ring]
