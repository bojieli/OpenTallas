read_db $::env(AUDIT_DB)
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set c [$b getCoreArea]
puts "ACTUAL_CORE [list [$c xMin] [$c yMin] [$c xMax] [$c yMax]] dbu=$u"
set f [open /audit/$::env(AUDIT_LABEL)_rows.tsv w];set ymin 1e99;set ymax -1e99;set area 0.0;set count 0;set pitch 0
foreach row [$b getRows] {
 set bb [$row getBBox];set h [[$row getSite] getHeight]
 set iy [expr {([$bb yMin]-[$c yMin])/double($h)}]
 puts $f [join [list [$row getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] $h $iy] "\t"]
 set ymin [expr {min($ymin,[$bb yMin])}];set ymax [expr {max($ymax,[$bb yMax])}]
 set area [expr {$area+double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$u/$u}];incr count
}
close $f
puts "ACTUAL_ROWS count=$count ymin=$ymin ymax=$ymax area_um2=$area"
foreach g [$b getGroups] {set r [$g getRegion];puts "ACTUAL_GROUP [$g getName] type=[$g getType] cells=[llength [$g getInsts]] region=[expr {$r eq "NULL"?"NULL":[$r getName]}]"}
set f [open /audit/$::env(AUDIT_LABEL)_cells.tsv w];set groups [dict create];set pg_b 0;set pg_u 0;set idnt 0;set ndnt 0
foreach n [$b getNets] {if {[$n isDoNotTouch]} {incr ndnt}}
foreach i [$b getInsts] {
 set m [$i getMaster];set g [$i getGroup];set gn [expr {$g eq "NULL" ? "UNGROUPED" : [$g getName]}]
 if {[$i isDoNotTouch]} {incr idnt}
 set missing 0
 foreach p [$i getITerms] {
  if {[[$p getMTerm] getSigType] in {POWER GROUND}} {if {[$p getNet] eq "NULL"} {incr missing;incr pg_u} else {incr pg_b}}
 }
 dict incr groups $gn
 puts $f [join [list [$i getName] [$m getName] [$m getType] $gn [$i getPlacementStatus] [$i isDoNotTouch] $missing] "\t"]
}
close $f
puts "ACTUAL_PG bound=$pg_b unbound=$pg_u inst_dnt=$idnt net_dnt=$ndnt membership=$groups"
set p /OpenROAD-flow-scripts/flow/scripts/detail_place.tcl
if {[file isfile $p]} {set f [open $p];set lines [split [read $f] "\n"];close $f;puts "ACTUAL_DPL_SOURCE_LINES [lrange $lines 35 45]"}
