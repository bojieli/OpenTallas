read_db /checkpoint/5_1_grt.odb
set b [ord::get_db_block]
set r [$b findRegion cp_body]
if {$r eq "NULL"} {error "Missing actual cp_body region"}
# Disjoint unused upper-right part of SAME core, native54x270 DBU site grid.
# cp_association remains [17280,56160,22464,60480].
odb::dbBox_create $r 22464 56160 60480 60480
source /contract/cp_r3_membership.tcl
detailed_placement
check_placement -verbose
write_db /output/reallocated_context.odb
puts OT_CP_R3_FINITE_REALLOCATION_PLACEMENT_PASS
