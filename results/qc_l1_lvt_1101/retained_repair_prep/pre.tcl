# UNRUN private reviewed-guide retained-route PREP; no GRT/resize/CTS.
source /work/route_guard_pre.tcl
if {[[ord::get_db_block] getDbUnitsPerMicron] != 1000} {error "L1 guide PREP expects actual1000DBU/um"}
set ::l1_retained_inst_count [llength [[ord::get_db_block] getInsts]]
set n [[ord::get_db_block] findNet {u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]}]
if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [$n isSpecial]} {error "L1 target must be ordinary SIGNAL"}
if {[$n getWire] eq "NULL"} {error "L1 genuine detailed target wire absent"}
write_guides /work/retained_repair/original.guide
exec python3 /work/retained_repair/patch_guides.py /work/retained_repair/original.guide /work/retained_repair/candidate.guide /work/retained_repair/proposed_guides.json
read_guides /work/retained_repair/candidate.guide
odb::dbWire_destroy [$n getWire]
puts {L1_EXPLICIT_TARGET_WIRE_RIPPED_ONLY; ordinary detailed_route has broader native visibility, postguard required}
