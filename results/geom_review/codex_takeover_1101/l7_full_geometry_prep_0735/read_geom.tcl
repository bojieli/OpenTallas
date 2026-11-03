# Read-only native geometry observer. No SDC/Liberty analysis or mutating command.
read_db /work/input.odb
set ::env(OT_GEOM_OUT) /work/geom.tsv
uplevel #0 [list source /work/geom_dump.tcl]
set total 0;set opens 0;set wrong 0
foreach i [[ord::get_db_block] getInsts] {
 foreach it [$i getITerms] {
  set type [[$it getMTerm] getSigType]
  if {$type ni {POWER GROUND}} {continue}
  incr total;set n [$it getNet]
  if {$n eq "NULL"} {incr opens} elseif {[$n getSigType] ne $type} {incr wrong}
 }
}
set f [open /work/pg_census.json w]
puts $f [format {{"checked":%d,"open":%d,"wrong_type":%d}} $total $opens $wrong];close $f
# Canonical native body/block-obstruction context. Macro master layer masks are
# the O records in geom.tsv. These are actual saved objects, no inferred halos.
set f [open /work/native_obstacles.tsv w]
set u [expr {double([[ord::get_db_block] getDbUnitsPerMicron])}]
foreach i [[ord::get_db_block] getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 set b [$i getBBox]
 puts $f [join [list MACRO [$i getName] [[$i getMaster] getName] [expr {[$b xMin]/$u}] [expr {[$b yMin]/$u}] [expr {[$b xMax]/$u}] [expr {[$b yMax]/$u}]] "\t"]
}
foreach o [[ord::get_db_block] getObstructions] {
 set b [$o getBBox];set l [$b getTechLayer]
 puts $f [join [list BLOCK_OBS [$l getName] [expr {[$b xMin]/$u}] [expr {[$b yMin]/$u}] [expr {[$b xMax]/$u}] [expr {[$b yMax]/$u}]] "\t"]
}
close $f
puts "L7_READONLY_GEOM_CLOSED PG=$total open=$opens wrong=$wrong"
