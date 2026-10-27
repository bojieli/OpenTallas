export PRE_GLOBAL_ROUTE_TCL = /work/pre_grt_r5.tcl
export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_r5.tcl
export OT_MSCTS_SPEC = /work/mscts_spec_r5.tcl

# ---- QC-CORES-1 btab_m0_r7 (2026-10-27): r5 kit (same synth + floorplan + SRAM sites + corner keep-offs + leg keep-off) with
# (1) GEOM-REVIEW-7 cond: E read-mux placed in a bounded-density grid (pre_gpl_r7.tcl, 2 stages x 4 cols x 8 bands) instead of
# one region; (2) MODEL-REFIT-3 RCX-window cause (island size 5-18 leaves): planner su_tree_uf_ls_r7.py assigns sinks to islands
# with EQUAL load (maze-distance balanced), spec mscts_spec_r7.tcl.  ITERS 0, TritonCTS off, no pads/trims.
export DESIGN_NICKNAME = kq_qfd_dv_s8x_btab_mif0r7
export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_r7.tcl
export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_r7.tcl
export OT_MSCTS_SPEC = /work/mscts_spec_r7.tcl
