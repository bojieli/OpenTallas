# Read-only actual post-place technology/occupancy snapshot. No placement or net edits.
read_db $::env(ODB)
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
puts $f [list DBU $u]
set box [$b getCoreArea];puts $f [list CORE [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
foreach row [$b getRows] {
 set box [$row getBBox];set site [$row getSite]
 puts $f [list ROW [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$site getWidth] [$row getOrient]]
}
foreach inst [$b getInsts] {
 if {[$inst getPlacementStatus] in {NONE UNPLACED}} continue
 set box [$inst getBBox]
 puts $f [list OBSTACLE [$inst getName] placed [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
}
foreach block [$b getBlockages] {
 if {[$block isSoft] || [$block getMaxDensity]>0} continue
 set box [$block getBBox]
 puts $f [list OBSTACLE blockage_[$block getId] hard [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
}
foreach name {BUFx8_ASAP7_75t_R BUFx10_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R} {
 set master [[ord::get_db] findMaster $name]
 if {$master eq "NULL"} {error "missing driver master $name"}
 puts $f [list MASTER $name [$master getWidth] [$master getHeight]]
}
close $f
puts FLAT_CLOCK_NATIVE_SITES_DONE
