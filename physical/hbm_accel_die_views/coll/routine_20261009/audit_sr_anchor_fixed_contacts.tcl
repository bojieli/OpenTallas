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
set macro_boxes {};set fixed_rows [dict create]
foreach inst [$block getInsts] {
 set bb [$inst getBBox];set name [$inst getName]
 if {[[$inst getMaster] isBlock]} {lappend macro_boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] $name];continue}
 if {[$inst getPlacementStatus] in {FIRM LOCKED COVER}} {
  dict lappend fixed_rows [$bb yMin] [list [$bb xMin] [$bb xMax] $name]
 }
}
set badmacro [dict create];set badfixed [dict create];set examples 0
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 set bb [$inst getBBox];set x0 [$bb xMin];set y0 [$bb yMin];set x1 [$bb xMax];set y1 [$bb yMax]
 foreach mb $macro_boxes {
  lassign $mb mx0 my0 mx1 my1 mn
  if {$x0<$mx1&&$x1>$mx0&&$y0<$my1&&$y1>$my0} {
   dict set badmacro $name 1
   if {$examples<12} {puts "SR_ANCHOR_MACRO_OVERLAP $name $mn";incr examples}
  }
 }
 if {![dict exists $fixed_rows $y0]} continue
 foreach fc [dict get $fixed_rows $y0] {
  lassign $fc fx0 fx1 fn
  if {$name ne $fn&&$x0<$fx1&&$x1>$fx0} {
   dict set badfixed $name 1
   if {$examples<12} {puts "SR_ANCHOR_FIXED_CELL_OVERLAP $name $fn";incr examples}
  }
 }
}
puts "SR_ANCHOR_EXTERNAL_FIXED_CONTACTS macros=[dict size $badmacro] fixed_std=[dict size $badfixed] anchors=[dict size $anchors]"
puts "SR_EXTERNAL_CONTACT_READ_ONLY_COMPLETE"
exit
