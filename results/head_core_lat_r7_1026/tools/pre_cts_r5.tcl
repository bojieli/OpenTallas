# HEAD-CORE-LAT-R5 PRE_CTS (CALIBRATION build, non-gating): plan-built in-core tree from OT_MSCTS_SPEC (head_tree_plan.py,
# R7: same tree hook as the R5 calibration builds; spec = r7b_f5_24444_b0 (fringe-weighted leaves) on the elemB_r6 3_place geometry.
# computed on this kit's 3_place geometry before the build; no measured input), hung on the 12.2a1 island root u_isl_root.
# TritonCTS off (OT_H_NO_TRITON 1), no pads / trims / ECO (12.8).
source /work/cf/mscts_core.tcl
source /work/cf/mscts_h_head.tcl
ot_ms_build
