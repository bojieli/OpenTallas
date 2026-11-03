read_db /input/input.odb
set n [[ord::get_db_block] findNet {u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]}]
if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || [$n isSpecial] || [$n getWire] eq "NULL"} {error "target input mismatch"}
write_guides /prep/original.guide
exec python3 /prep/patch_guides.py /prep/original.guide /prep/candidate.guide /prep/proposed_guides.json
read_guides /prep/candidate.guide
odb::dbWire_destroy [$n getWire]
write_db /prep/TARGET_RIPPED_GUIDE_INPUT.odb
