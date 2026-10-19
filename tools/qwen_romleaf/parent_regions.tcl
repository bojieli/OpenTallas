# Q-ROMPARENT (2026-10-16 18:40): consumer/region ownership of every parent soft-root sink.
# Gate3 (qfd_tile_nk_romleaf_a0, E4 ...-162604) measured why the shared roots fail: ck 10644 sinks TT 556..1230 ps
# (one root over the whole 442 x 692 um field: TX rungs of all eight LSLs, ME, both ROM columns), ck_rs/ck_rn
# 1024 sinks each spanning both ROM gutters (303..404 / 410..821 ps).  Each root is now owned by ONE compact
# region beside its consumer; every root is a separate compensated die entry (no logical edge changes).
# The caller supplies qrl_groups: an ordered list of {name type regex boxes min max}.  Each sequential standard cell
# joins the FIRST group whose regex matches its backslash-stripped name; regions/groups are created in odb.
if {![info exists qrl_groups]} {error "ROMleaf parent region groups absent"}
set qrl_block [ord::get_db_block]
set qrl_dbu [$qrl_block getDbUnitsPerMicron]
set qrl_members [dict create]
foreach g $qrl_groups { dict set qrl_members [dict get $g name] {} }
foreach inst [$qrl_block getInsts] {
 set master [$inst getMaster]
 if {[$master isBlock] || ![$master isSequential]} {continue}
 set name [string map [list "\\" ""] [$inst getName]]
 foreach g $qrl_groups {
  if {[regexp [dict get $g regex] $name]} { dict lappend qrl_members [dict get $g name] $inst; break }
 }
}
set report [open qrl_parent_regions.tsv w]
puts $report "group\ttype\tff_sinks\tcell_area_um2\trow_capacity_um2\tfill\tboxes"
foreach g $qrl_groups {
 set gname [dict get $g name]
 set members [dict get $qrl_members $gname]
 set n [llength $members]
 if {$n < [dict get $g min] || $n > [dict get $g max]} {
  error "ROMleaf parent region $gname owns $n sequential cells, expected [dict get $g min]..[dict get $g max]"
 }
 # FREE (Q-A0FIX2 10-19): the group only CLAIMS its registers (so no later group, e.g. the catch-all hub, boxes them);
 # no region is created and global placement puts each one between its driver and its loads.  Used for the landing
 # register of an entry crossing (TX rung 0, ROM request relay, fault capture): one register -> wire -> register hop
 # each side instead of one > 405 um hop boxed at either end.
 if {[dict get $g type] eq "FREE"} {
  puts $report "$gname\tFREE\t$n\t-\t-\t-\t-"
  puts "QRL_REGION $gname FREE sinks=$n"
  continue
 }
 set region [odb::dbRegion_create $qrl_block qrl_$gname]
 $region setRegionType [dict get $g type]
 set capacity 0.0
 foreach box [dict get $g boxes] {
  lassign $box x0 y0 x1 y1
  odb::dbBox_create $region [expr {round($x0*$qrl_dbu)}] [expr {round($y0*$qrl_dbu)}] [expr {round($x1*$qrl_dbu)}] [expr {round($y1*$qrl_dbu)}]
  foreach row [$qrl_block getRows] {
   set bb [$row getBBox]
   set rx0 [expr {[$bb xMin]/double($qrl_dbu)}];set ry0 [expr {[$bb yMin]/double($qrl_dbu)}]
   set rx1 [expr {[$bb xMax]/double($qrl_dbu)}];set ry1 [expr {[$bb yMax]/double($qrl_dbu)}]
   set capacity [expr {$capacity+max(0.0,min($x1,$rx1)-max($x0,$rx0))*max(0.0,min($y1,$ry1)-max($y0,$ry0))}]
  }
 }
 set group [odb::dbGroup_create $region qrl_$gname]
 set area 0.0
 foreach inst $members {
  if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} {error "ROMleaf region sink already owned: [$inst getName]"}
  $group addInst $inst
  set m [$inst getMaster]
  set area [expr {$area+double([$m getWidth])*[$m getHeight]/($qrl_dbu*$qrl_dbu)}]
 }
 # sequential area only: the combinational cone follows; keep the registers well below the row capacity
 if {$capacity<=0 || $area/$capacity>0.35} {error "ROMleaf region $gname cannot hold its registers: $area / $capacity"}
 puts $report "$gname\t[dict get $g type]\t$n\t$area\t$capacity\t[expr {$area/$capacity}]\t[dict get $g boxes]"
 puts "QRL_REGION $gname [dict get $g type] sinks=$n area=$area capacity=$capacity"
}
close $report
puts "ROMLEAF_PARENT_REGIONS_PASS [llength $qrl_groups] groups"
