# HBM-CORE-LAT-R5 hfd_ep_static (HBM-EP-CAL-1 calibration) PRE_CTS: plan-built structured clock = core_infra_htree R6 --no-pad (no level padding)
# (no per-branch sizing in this calibration) -> mscts_spec.tcl; QC mscts_core.tcl + mscts_h.tcl, TritonCTS off,
# no pads/trims/balance (OT_MSCTS_ITERS=0).  I3 nb10,6,10,6 smax150 no-pad, UNSIZED (plan sw/I3_nb106106_m150).
set _b [[ord::get_db_block] findBTerm clk]
foreach _p [$_b getBPins] { foreach _x [$_p getBoxes] { puts [format "OT_R5_CLKPIN %s %.3f %.3f %.3f %.3f" [[$_x getTechLayer] getName] [expr {[$_x xMin]/1000.0}] [expr {[$_x yMin]/1000.0}] [expr {[$_x xMax]/1000.0}] [expr {[$_x yMax]/1000.0}]] } }
source /work/cf/mscts_core.tcl
source /work/cf/mscts_h.tcl
ot_ms_build
