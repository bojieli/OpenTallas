read_db /input/6_final.odb
proc signature {} {
 set b [ord::get_db_block];set result {}
 foreach r [$b getRegions] {
  set boxes {};foreach box [$r getBoundaries] {lappend boxes [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
  lappend result [$r getName] [lsort $boxes]
 }
 foreach g [$b getGroups] {set names {};foreach i [$g getInsts] {lappend names [$i getName]};lappend result [$g getName] [lsort $names]}
 foreach p [$b getBTerms] {lappend result [$p getName] [[$p getNet] getName] [$p getIoType] [$p getSigType]}
 foreach i [$b getInsts] {lappend result [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]}
 foreach n [$b getNets] {
  foreach w [$n getSWires] {foreach box [$w getWires] {lappend result [$n getName] [$box isVia] [$box xMin] [$box yMin] [$box xMax] [$box yMax]}}
 }
 return $result
}
set before [signature]
set hf [open /task/lagrange-cp-access-out/pins_only.tcl r]
set hook [read $hf]; close $hf
set bad [string map [list {{clk}} {{__negative_missing_cp_pin__}}] $hook]
if {![catch {eval $bad} reason] || ![string match {*Missing pin*} $reason]} {error "Missing-pin preflight negative failed: $reason"}
if {$before ne [signature]} {error "Negative hook partially mutated DB"}
puts "OT_CP_NATIVE_NEGATIVE missing_pin_before_write=PASS"
source /task/lagrange-cp-access-out/pins_only.tcl
if {$before ne [signature]} {error "Non-pin structural/PG state mutated"}
set f [open /task/lagrange-cp-access-out/native_pin_check.tsv w]
foreach name $ot_pin_names {
 set p [[ord::get_db_block] findBTerm $name]
 set shapes 0
 foreach bp [$p getBPins] {foreach box [$bp getBoxes] {
  incr shapes
  puts $f "$name\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }}
 if {$shapes!=1} {error "Duplicate or missing shape $name: $shapes"}
}
close $f
puts "OT_CP_NATIVE_CHECK same_regions_groups_cells_nets_PG=PASS pins=236"
