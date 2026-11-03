# UNRUN private reviewed-guide retained-route PREP; no GRT/resize/CTS.
source /work/route_guard_pre.tcl
if {[[ord::get_db_block] getDbUnitsPerMicron] != 1000} {error "L1 guide PREP expects actual1000DBU/um"}
set ::l1_retained_inst_count [llength [[ord::get_db_block] getInsts]]
set n [[ord::get_db_block] findNet {u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]}]
if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [$n isSpecial]} {error "L1 target must be ordinary SIGNAL"}
if {[$n getWire] eq "NULL"} {error "L1 genuine detailed target wire absent"}
write_guides /repair/original.guide
exec python3 /repair/patch_guides.py /repair/original.guide /repair/candidate.guide /repair/proposed_guides.json
read_guides /repair/candidate.guide
odb::dbWire_destroy [$n getWire]
puts {L1_EXPLICIT_TARGET_WIRE_RIPPED_ONLY; ordinary detailed_route has broader native visibility, postguard required}
