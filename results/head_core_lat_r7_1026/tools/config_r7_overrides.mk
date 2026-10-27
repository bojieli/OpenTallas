
# ---- HEAD-CORE-LAT-R7 elemB clock-structure build (COORD 18:4x): plan-built in-core tree r7b_f5_24444_b0
# (head_tree_plan.py --fanouts 2,4,4,4,4 --fringe 8,1,6 on this kit's 3_place geometry, sha 84e5167c, before the build;
# no measured input), hung on the 12.2a1 island root u_isl_root; TritonCTS off, ITERS 0, no pads/trims/ECO.
# CTS + GRT, per-sink arrivals on GRT RC (rc_cal 0.8,0.9) = uf_phys3 basis.  GEOM-9 (a)(c) placement conditions still open.
override export PRE_CTS_TCL = /work/pre_cts_r5.tcl
override export OT_MSCTS_SPEC = /work/mscts_spec_r7.tcl
override export OT_MSCTS_ITERS = 0
override export OT_H_NO_TRITON = 1
override export OT_HEAD_CLK_NET = clk
override export OT_HEAD_ROOT_INST = u_isl_root
override export POST_CTS_TCL = /work/noop.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/noop.tcl
override export SKIP_INCREMENTAL_REPAIR = 1
override export MIN_CLK_ROUTING_LAYER = M4
override export MAX_CLK_ROUTING_LAYER = M5
