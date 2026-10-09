# Private-ODB existing-legalizer probe. Original source and database mounted read-only.
read_db $::env(OT_FAILED_ODB)
set block [ord::get_db_block]
set anchors [dict create]
# Preserve nearest sequential capture/launch seats reached from each actual signal pin.
foreach bt [$block getBTerms] {
 if {[$bt getSigType] ne "SIGNAL" || [regexp -nocase {^(ck|clk|pclk|refclk|rst|por)} [$bt getName]]} continue
 set net [$bt getNet]; if {$net eq "NULL"} continue
 set dir [$bt getIoType]; if {$dir ni {INPUT OUTPUT}} continue
 set queue [list $net];set seen [dict create]
 while {[llength $queue]} {
  set net [lindex $queue 0];set queue [lrange $queue 1 end]
  if {[dict exists $seen [$net getId]]} continue
  dict set seen [$net getId] 1
  foreach it [$net getITerms] {
   if {$dir eq "INPUT" && ![$it isInputSignal]} continue
   if {$dir eq "OUTPUT" && ![$it isOutputSignal]} continue
   set inst [$it getInst];set master [$inst getMaster]
   if {[$master isBlock]} continue
   if {[$master isSequential]} {
    dict set anchors [$inst getName] [list $inst [$inst getOrigin] [$inst getOrient]]
    continue
   }
   foreach next [$inst getITerms] {
    if {$dir eq "INPUT" && ![$next isOutputSignal]} continue
    if {$dir eq "OUTPUT" && ![$next isInputSignal]} continue
    if {[[$next getMTerm] getSigType] eq "CLOCK"} continue
    set nn [$next getNet];if {$nn ne "NULL"} {lappend queue $nn}
   }
  }
 }
}
puts "SR_PROBE_PIN_ANCHORS [dict size $anchors]"
set rows [dict create]
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 set bb [$inst getBBox];set x [$bb xMin];set y [$bb yMin]
 dict lappend rows $y [list $x [$bb xMax] $name]
}
set overlaps 0;set printed 0
foreach y [dict keys $rows] {
 set cells [lsort -integer -index 0 [dict get $rows $y]]
 set maxend -1;set prev ""
 foreach seat $cells {
  lassign $seat x end name
  if {$x<$maxend} {
   incr overlaps
   if {$printed<12} {puts "SR_REQUIRED_ANCHOR_OVERLAP row=$y left=$prev right=$name x=$x prior_end=$maxend";incr printed}
  }
  if {$end>$maxend} {set maxend $end;set prev $name}
 }
}
puts "SR_REQUIRED_ANCHOR_BBOX_OVERLAPS $overlaps"
puts "SR_ANCHOR_READ_ONLY_COMPLETE"
exit
