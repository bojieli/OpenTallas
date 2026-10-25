# QC-PHYS f57 PRE_CTS = kit hold_budget.tcl (dont_touch lift for CTS), then the max-wire structural rule (main
# physical/common_flow/max_wire_repeat.tcl default 80 um: f56c's 12 routed slew violators 336-509 ps were single
# BUFx3 -> INVx1 nets of 167-179 um, unrepeated), then F5 regional taps + macro leaves.
source /work/hold_budget.tcl
estimate_parasitics -placement
set ot_mw0 [sta::network_leaf_instance_count]
repair_design -max_wire_length [expr {[info exists ::env(OT_MAX_WIRE_UM)] ? $::env(OT_MAX_WIRE_UM) : 80}] -slew_margin 20 -cap_margin 20
detailed_placement
puts "OT_MAXWIRE pre-CTS repair_design -max_wire_length: leaf instances $ot_mw0 -> [sta::network_leaf_instance_count]"
source /work/move_rsel.tcl
source /work/core_taps.tcl
