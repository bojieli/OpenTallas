# QC-SU-LAT rp1 variant M: cts_pre.tcl with core_taps.tcl replaced by the structured MSCTS build
source /work/hold_budget.tcl
estimate_parasitics -placement
repair_design -max_wire_length [expr {[info exists ::env(OT_MAX_WIRE_UM)] ? $::env(OT_MAX_WIRE_UM) : 80}] -slew_margin 20 -cap_margin 20
detailed_placement
source /work/move_rsel.tcl
source /work/cf/mscts_core.tcl
ot_ms_build
