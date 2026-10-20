# KV-RST3 2026-10-20 (s32v4, spec "pre_cts_extra"): release the HROOT centre fence (central_fence_s32v4.tcl) before CTS.
# GPL + DPL have already placed the fenced cells inside the box; CTS clock buffers / clkload cells and hold-repair buffers
# are not group members, and opendp forbids non-members inside the region, so post-CTS legalisation overlapped at the
# fence edge (s32v4 gate1: DPL-0033, 14 overlaps).  After this hook post-CTS DPL only nudges cells (max displacement
# small), so the centre placement -- and the <=380 um stage reach -- stays; the routed reach audit checks it.
set fr_b [ord::get_db_block]
set fr_r [$fr_b findRegion ot_hroot_center80]
if {$fr_r eq "NULL"} { error "HROOT_CENTER release: region ot_hroot_center80 absent (fence hook did not run?)" }
set fr_n 0
foreach fr_g [$fr_r getGroups] {
  foreach fr_i [$fr_g getInsts] { $fr_g removeInst $fr_i; incr fr_n }
  odb::dbGroup_destroy $fr_g
}
odb::dbRegion_destroy $fr_r
puts "HROOT_CENTER released fence: $fr_n members ungrouped, region removed before CTS"
