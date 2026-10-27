override export PLACE_DENSITY = 0.50

# ---- HEAD-CORE-LAT-R5 CALIBRATION build (non-gating, COORD RULING HEAD-CORE-LAT-R4 step 4): plan-built in-core tree
# (head_tree_plan.py on this kit 3_place geometry, spec computed before the build) on the 12.2a1 island root; TritonCTS off,
# ITERS 0, no pads/trims/ECO; CTS + GRT only, clock arrivals measured on GRT RC (rc_cal 0.8,0.9) to refit uf_phys for HEAD.
override export PRE_CTS_TCL = /work/pre_cts_r5.tcl
override export OT_MSCTS_SPEC = /work/mscts_spec_r5.tcl
override export OT_MSCTS_ITERS = 0
override export OT_H_NO_TRITON = 1
override export OT_HEAD_CLK_NET = clk
override export OT_HEAD_ROOT_INST = u_isl_root
override export POST_CTS_TCL = /work/noop.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/noop.tcl
override export SKIP_INCREMENTAL_REPAIR = 1
override export MIN_CLK_ROUTING_LAYER = M4
override export MAX_CLK_ROUTING_LAYER = M5
override export PLACE_DENSITY = 0.5 (n50) / 0.65 (n65)
pre_gpl_island.tcl: v4q kit minus the 8 Codex quadrant CT_* placeholder cells (pi_cell CT_*)
