# ---- QC-SU-BTAB-R5 (2026-10-26) GEOM-REVIEW-6 16:23 structural fix on the btab_m0_r4 kit (same synth + floorplan + macro sites,
# same clock planner and parameters -- no clock-rule change): (1) PRE_GLOBAL_ROUTE M2-M5 routing keep-off at every SRAM pin-face
# corner + gap-centre entry (pre_grt_r5.tcl); (2) PRE_GLOBAL_PLACE partial blockage beside the E pin-flop column so the free logic
# spreads into x 255-340 (pre_gpl_r5.tcl); re-placed, plan re-run on this placement with tree legs kept off the SRAM clock-pin
# columns (+4.32) except through gap centres (Q0 L1 off x 233), spec mscts_spec_r5.tcl. ITERS 0, TritonCTS off, no pads/trims.
export DESIGN_NICKNAME = kq_qfd_dv_s8x_btab_mif0r5
export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_r5.tcl
export PRE_GLOBAL_ROUTE_TCL = /work/pre_grt_r5.tcl
export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_r5.tcl
export OT_MSCTS_SPEC = /work/mscts_spec_r5.tcl
