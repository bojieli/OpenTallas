read_db /input/5_1_grt-failed.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set d [$b getDieArea]
set c [$b getCoreArea]
set a 0.0
set buffers 0
set ties 0
foreach i [$b getInsts] {
 set m [$i getMaster]
 set a [expr {$a+double([$m getWidth])*[$m getHeight]/$u/$u}]
 if {[string match *BUF* [$m getName]]} {incr buffers}
 if {[string match TIE* [$m getName]]} {incr ties}
}
set f [open /output/geometry.tsv w]
puts $f "die_area_um2	[expr {double([$d dx])*[$d dy]/$u/$u}]"
puts $f "core_area_um2	[expr {double([$c dx])*[$c dy]/$u/$u}]"
puts $f "cell_area_um2	$a"
puts $f "core_width_um	[expr {double([$c dx])/$u}]"
puts $f "core_height_um	[expr {double([$c dy])/$u}]"
puts $f "cell_count	[llength [$b getInsts]]"
puts $f "buffer_cell_count	$buffers"
puts $f "tie_cell_count	$ties"
close $f
exit
