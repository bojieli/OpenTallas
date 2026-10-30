read_db /work/fixed_probe.odb
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set f [open /work/fixed_sites.tsv w]
foreach i [$b getInsts] {
 set st [$i getPlacementStatus]
 if {$st ni {FIRM LOCKED COVER}} continue
 set r [$i getBBox]
 puts $f "[$i getName]\t[[$i getMaster] getName]\t$st\t[expr {[$r xMin]/double($dbu)}]\t[expr {[$r yMin]/double($dbu)}]\t[expr {[$r xMax]/double($dbu)}]\t[expr {[$r yMax]/double($dbu)}]"
}
close $f
