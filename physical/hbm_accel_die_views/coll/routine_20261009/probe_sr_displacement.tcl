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
set bad 0
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 if {[lindex $xy 0]%54 || ([lindex $xy 1]-540)%270} {incr bad;puts "SR_ANCHOR_OFFGRID $name $xy"}
 $inst setPlacementStatus FIRM
}
if {$bad} {error "Required existing pin anchors offgrid; do not legalize/move anchors"}
# Runtime-confirmed30x23 MICRON sensitivity. Not the8.10x6.21um adoption budget.
# Preserve this advancing probe; inspect actual movements before any bounded successor.
detailed_placement -max_displacement {30 23}
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 if {[$inst getOrigin] ne $xy || [$inst getOrient] ne $orient} {error "Required anchor moved: $name"}
}
puts "SR_PIN_ANCHORS_UNCHANGED"
write_db /probe/sr-displacement-30x23.odb
check_placement -verbose
puts "SR_DISPLACEMENT_PROBE_PLACEMENT_PASS"
exit
