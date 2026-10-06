read_db /checkpoint/cts_failure.odb
source /contract/cts_membership.tcl
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
write_db /output/clock_membership.odb
puts OT_CP_CTS_MEMBERSHIP_DPL_PASS
