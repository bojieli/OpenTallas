# FLOW-CLOCK-R7: signoff.py-style DRV count on a routed DB with RCX parasitics, one corner (the measure of the
# post_route_drv loop; same counters signoff.py reads: sta::max_slew/capacitance_violation_count).  Env: OT_LEFS OT_LIBS
# ODB SDC SPEF (extracted with RCX_RULES and written when missing) TAG CHKPL (1 = check_placement first)
foreach l $::env(OT_LEFS) { read_lef $l }
foreach l $::env(OT_LIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
if {![file exists $::env(SPEF)]} { extract_parasitics -ext_model_file $::env(RCX_RULES); write_spef $::env(SPEF) }
read_spef $::env(SPEF)
set pl ok
if {$::env(CHKPL) eq "1"} { if {[catch {check_placement -verbose} m]} { set pl "FAIL $m" } }
puts [format "OT_PRD_COUNT %s slew %d cap %d placement %s" $::env(TAG) [sta::max_slew_violation_count] [sta::max_capacitance_violation_count] $pl]
exit
