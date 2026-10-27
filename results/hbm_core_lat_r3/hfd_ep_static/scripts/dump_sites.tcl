# HBM-CORE-LAT-R3: sites file for core_plan_to_infra.py (ROW0/ROW/FIXED/MASTER/PG) from a kit 2_4_floorplan_pdn.odb.
# env ODB OUT.  Read-only.
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.4f [expr {$v / double($::u)}]] }
set f [open $::env(OUT) w]
set rows [$b getRows]; set r0 [lindex $rows 0]; set s [$r0 getSite]
set o [$r0 getOrigin]
puts $f "ROW0 [um [lindex $o 0]] [um [lindex $o 1]] site_w [um [$s getWidth]] site_h [um [$s getHeight]] nrows [llength $rows] nsites [$r0 getSiteCount]"
foreach r $rows { set o [$r getOrigin]; puts $f "ROW [um [lindex $o 0]] [um [lindex $o 1]] [$r getOrient] [$r getSiteCount]" }
foreach i [$b getInsts] {
  if {[$i isFixed] || [[$i getMaster] isBlock]} { set q [$i getBBox]
    puts $f "FIXED [$i getName] [[$i getMaster] getName] [um [$q xMin]] [um [$q yMin]] [um [$q xMax]] [um [$q yMax]]" }
}
foreach lib [[ord::get_db] getLibs] { foreach m [$lib getMasters] {
  if {[string match {BUF*} [$m getName]] || [string match {INV*} [$m getName]]} { puts $f "MASTER [$m getName] [um [$m getWidth]] [um [$m getHeight]]" } } }
foreach n [$b getNets] { if {[$n getSigType] ne "POWER" && [$n getSigType] ne "GROUND"} continue
  foreach sw [$n getSWires] { foreach bx [$sw getWires] { if {[$bx isVia]} continue
    set l [[$bx getTechLayer] getName]; if {$l ne "M4" && $l ne "M5"} continue
    puts $f "PG [$n getName] $l [um [$bx xMin]] [um [$bx yMin]] [um [$bx xMax]] [um [$bx yMax]]" } } }
close $f; puts "DUMP_SITES done"; exit
