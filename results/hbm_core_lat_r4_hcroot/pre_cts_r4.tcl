# HBM-CORE-LAT-R4 hcp_sys1 PRE_CTS: (1) GEOM-REVIEW-16 01:11 PASS-COND: snap the centre M5 clock pin from the half-track
# x=77.76 to 77.784 (M5 lattice 0.024+k*0.048, k=1620); same layer/size as io.tcl. (2) plan-built structured H-tree
# (core_infra_htree R6 spec = R3 hcp_sys1.tree_spec.tcl, port renamed ck->clk), QC mscts_core.tcl + mscts_h.tcl,
# TritonCTS off (OT_H_NO_TRITON=1), no pads/trims/balance (OT_MSCTS_ITERS=0), frozen named leaf membership.
place_pin -pin_name {clk} -layer M5 -location {77.784 86.4} -pin_size {0.032 0.192}
set _b [[ord::get_db_block] findBTerm clk]
foreach _p [$_b getBPins] { foreach _x [$_p getBoxes] { puts [format "OT_R4_CLKPIN %s %.3f %.3f %.3f %.3f" [[$_x getTechLayer] getName] [expr {[$_x xMin]/1000.0}] [expr {[$_x yMin]/1000.0}] [expr {[$_x xMax]/1000.0}] [expr {[$_x yMax]/1000.0}]] } }
source /work/cf/mscts_core.tcl
source /work/cf/mscts_h.tcl
ot_ms_build
