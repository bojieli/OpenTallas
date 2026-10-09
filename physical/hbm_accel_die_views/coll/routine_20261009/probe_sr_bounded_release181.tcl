# Private-ODB existing-legalizer probe. Original source and database mounted read-only.
read_db $::env(OT_FAILED_ODB)
set block [ord::get_db_block]
set anchors [dict create]
set pin_links [dict create]
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
    dict lappend pin_links [$inst getName] [$bt getName]
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
puts "SR_BOUNDED_ANCHOR_COUNT [dict size $anchors]"
set rows [dict create]
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 set bb [$inst getBBox]
 dict lappend rows [$bb yMin] [list [$bb xMin] [$bb xMax] $name]
}
set released [dict create]
foreach y [dict keys $rows] {
 set maxend -1
 foreach seat [lsort -integer -index 0 [dict get $rows $y]] {
  lassign $seat x end name
  if {$x<$maxend} {dict set released $name 1}
  set maxend [expr {max($maxend,$end)}]
 }
}
if {[dict size $released]!=181} {error "Expected exactly181 confirmed overlapping right-contact anchors"}
set af [open /probe/sr-bounded-released-anchors.txt w]
foreach name [lsort [dict keys $released]] {puts $af $name}
close $af
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 if {![dict exists $released $name]} {$inst setPlacementStatus FIRM}
}
set macro_orig [dict create]
set all_orig [dict create]
foreach inst [$block getInsts] {
 dict set all_orig [$inst getName] [$inst getOrigin]
 if {[[$inst getMaster] isBlock]} {dict set macro_orig [$inst getName] [list [$inst getOrigin] [$inst getOrient]]}
}
set bt_orig [dict create]
foreach bt [$block getBTerms] {
 set geom {}
 foreach pin [$bt getBPins] {foreach box [$pin getBoxes] {lappend geom [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
 dict set bt_orig [$bt getName] $geom
}
# OpenROAD arguments are microns:150 sites X and23 rows Y.
if {[info exists ::env(OT_SR_CHECK_ONLY_ODB)]} {
 read_db $::env(OT_SR_CHECK_ONLY_ODB)
 set block [ord::get_db_block]
 set instmap [dict create]
 foreach inst [$block getInsts] {dict set instmap [$inst getName] $inst}
 foreach name [dict keys $anchors] {
  lassign [dict get $anchors $name] oldinst xy orient
  if {![dict exists $instmap $name]} {error "Missing anchor $name"}
  dict set anchors $name [list [dict get $instmap $name] $xy $orient]
 }
 set rc 0;set err ""
 # Minimum in-memory wrong-movement negative; never writes candidate output.
 if {[info exists ::env(OT_SR_WRONG_MOVEMENT)]} {
  set name [lindex [lsort [dict keys $released]] 0]
  lassign [dict get $anchors $name] inst xy orient
  $inst setLocation [expr {[lindex $xy 0]+8154}] [lindex $xy 1]
  puts "SR_WRONG_MOVEMENT_INJECTED $name"
 }
} else {
 set rc [catch {detailed_placement -max_displacement {8.10 6.21}} err]
 # Retain private output even if existing legalizer reports failure.
 write_db /probe/sr-displacement-8p10x6p21-release181.odb
}
set btmap [dict create]
foreach bt [$block getBTerms] {dict set btmap [$bt getName] $bt}
set bad 0;set maxdx 0;set maxdy 0;set maxpin 0
set global_maxdx 0;set global_maxdy 0;set global_outside 0
foreach name [dict keys $anchors] {
 lassign [dict get $anchors $name] inst xy orient
 set now [$inst getOrigin]
 set dx [expr {abs([lindex $now 0]-[lindex $xy 0])}];set dy [expr {abs([lindex $now 1]-[lindex $xy 1])}]
 if {![dict exists $released $name]} {
  if {$dx||$dy||[$inst getOrient] ne $orient} {incr bad;puts "SR_LEGAL_ANCHOR_MOVED $name"}
 } else {
  set maxdx [expr {max($maxdx,$dx)}];set maxdy [expr {max($maxdy,$dy)}]
  if {$dx>8100||$dy>6210} {incr bad;puts "SR_RELEASED_ANCHOR_OUTSIDE_BUDGET $name $dx $dy"}
  set bb [$inst getBBox];set cx [expr {([$bb xMin]+[$bb xMax])/2.0}];set cy [expr {([$bb yMin]+[$bb yMax])/2.0}]
  foreach pinname [dict get $pin_links $name] {
   if {![dict exists $btmap $pinname]} {error "Missing actual pin $pinname"}
   set bt [dict get $btmap $pinname]
   set nearest Inf
   foreach pin [$bt getBPins] {foreach box [$pin getBoxes] {
    set px [expr {([$box xMin]+[$box xMax])/2.0}];set py [expr {([$box yMin]+[$box yMax])/2.0}]
    set nearest [expr {min($nearest,abs($cx-$px)+abs($cy-$py))}]
   }}
   set maxpin [expr {max($maxpin,$nearest)}]
   if {$nearest>100000} {incr bad;puts "SR_RELEASED_ANCHOR_PIN_DISTANCE_FAIL $name [$bt getName] $nearest"}
  }
 }
}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $all_orig $name]} {error "Unexpected source instance $name"}
 set xy [dict get $all_orig $name];set now [$inst getOrigin]
 set dx [expr {abs([lindex $now 0]-[lindex $xy 0])}];set dy [expr {abs([lindex $now 1]-[lindex $xy 1])}]
 set global_maxdx [expr {max($global_maxdx,$dx)}];set global_maxdy [expr {max($global_maxdy,$dy)}]
 if {$dx>8100||$dy>6210} {incr global_outside}
 if {![dict exists $macro_orig [$inst getName]]} continue
 if {[dict get $macro_orig [$inst getName]] ne [list [$inst getOrigin] [$inst getOrient]]} {incr bad;puts "SR_MACRO_MOVED [$inst getName]"}
}
foreach bt [$block getBTerms] {
 set geom {}
 foreach pin [$bt getBPins] {foreach box [$pin getBoxes] {lappend geom [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
 if {[dict get $bt_orig [$bt getName]] ne $geom} {incr bad;puts "SR_BTERM_MOVED [$bt getName]"}
}
puts "SR_ALL_CELL_DISPLACEMENT maxdxDBU=$global_maxdx maxdyDBU=$global_maxdy outside=$global_outside"
if {$global_outside} {incr bad}
puts "SR_BOUNDED_GEOMETRY anchors=[dict size $anchors] released=[dict size $released] maxdxDBU=$maxdx maxdyDBU=$maxdy maxpinManhattanDBU=$maxpin bad=$bad"
if {$rc} {puts "SR_BOUNDED_LEGALIZER_FAIL $err";exit 1}
if {$bad} {error "SR bounded geometry gate failed"}
check_placement -verbose
puts "SR_BOUNDED_LEGALIZATION_PASS"
exit
