# Geometry-only plan installation. No libraries/SDC/STA/GRT or clock timing repair.
read_db /work/input.odb
set_thread_count 4
set b [ord::get_db_block];set db [ord::get_db]
set rows {};set occupied {};set occ_n 0;set original_geometry {}
foreach r [$b getRows] {set q [$r getBBox];dict lappend rows [$q yMin] [list [$q xMin] [$q xMax] [$q yMax]]}
foreach i [$b getInsts] {
 set q [$i getBBox];set rec [list [$q xMin] [$q yMin] [$q xMax] [$q yMax] [$i getName]]
 for {set k [expr {[$q yMin]/270}]} {$k<=([$q yMax]-1)/270} {incr k} {dict lappend occupied $k $rec}
 dict set original_geometry [$i getName] [list [$q xMin] [$q yMin] [$q xMax] [$q yMax] [$i getOrient] [[$i getMaster] getName]]
 incr occ_n
}
set f [open /work/clock_bodies.tsv r];set planned {};set n 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name master a bb c d
 if {[$b findInst $name] ne "NULL"} {error "CLOCK_ALREADY_EXISTS $name"}
 set m [$db findMaster $master]
 if {$m eq "NULL" || [$m getWidth]!=$c-$a || [$m getHeight]!=$d-$bb} {error "CLOCK_MASTER_FOOTPRINT $name $master"}
 set fits 0
 if {[dict exists $rows $bb]} {foreach q [dict get $rows $bb] {lassign $q x0 x1 y1;if {$a>=$x0 && $c<=$x1 && $d<=$y1 && ($a-$x0)%54==0} {set fits 1;break}}}
 if {!$fits} {error "CLOCK_ROW_FIT $name"}
 for {set k [expr {$bb/270}]} {$k<=($d-1)/270} {incr k} {
  if {![dict exists $occupied $k]} {continue}
  foreach q [dict get $occupied $k] {lassign $q x0 y0 x1 y1 other;if {$a<$x1 && $c>$x0 && $bb<$y1 && $d>$y0} {error "CLOCK_OCCUPIED_SITE $name $other"}}
 }
 lappend planned [list $name $a $bb $c $d];incr n
}
close $f
puts "A0_ALL_CLOCK_BODY_RUNTIME_PASS nodes=$n existing_bodies=$occ_n"
set old {};set f [open /work/temporary_clock_blockages.tsv r]
while {[gets $f line]>=0} {dict set old [lrange [split $line "\t"] 0 3] 1}
close $f
set removed 0
foreach bo [$b getBlockages] {set q [$bo getBBox];set key [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]];if {[dict exists $old $key]} {odb::dbBlockage_destroy $bo;incr removed}}
puts "A0_TEMPORARY_CLOCK_BLOCKAGES_REMOVED $removed"
source /work/master_core_infra_late.tcl
check_placement -verbose
set maxd 0
foreach q $planned {
 lassign $q name x0 y0 x1 y1
 set i [$b findInst $name];set bb [$i getBBox]
 set dist [expr {abs([$bb xMin]-$x0)+abs([$bb yMin]-$y0)}]
 if {$dist>$maxd} {set maxd $dist}
 if {[$bb xMin]!=$x0 || [$bb yMin]!=$y0 || [$bb xMax]!=$x1 || [$bb yMax]!=$y1} {error "A0_INSTALLED_BODY_MOVED $name $dist"}
}
foreach name [dict keys $original_geometry] {
 set i [$b findInst $name];if {$i eq "NULL"} {error "ORIGINAL_INSTANCE_REMOVED $name"};set q [$i getBBox]
 set now [list [$q xMin] [$q yMin] [$q xMax] [$q yMax] [$i getOrient] [[$i getMaster] getName]]
 if {$now ne [dict get $original_geometry $name]} {error "ORIGINAL_INSTANCE_GEOMETRY_CHANGED $name"}
}
puts "A0_ALL_ORIGINAL_GEOMETRY_UNCHANGED [dict size $original_geometry]"
puts "A0_CLOCK_INSTALLED_GEOMETRY_PASS nodes=$n max_body_displacement_dbu=$maxd"
write_db /work/clock_installed.odb
set ::env(OT_GEOM_OUT) /work/geom_clock_installed.tsv
source /work/geom_dump.tcl
