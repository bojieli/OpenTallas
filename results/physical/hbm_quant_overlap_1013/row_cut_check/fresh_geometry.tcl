read_db $::env(OV_FRESH_DB)
set b [ord::get_db_block]
set f [open /work/fresh_geometry.tsv w]
foreach r [$b getRows] {
 puts $f [join [list ROW [$r getName] [[$r getSite] getName] {*}[$r getOrigin] [$r getOrient] [$r getDirection] [$r getSiteCount] [$r getSpacing]] "\t"]
}
set taps 0; set seam 0
foreach i [$b getInsts] {
 if {[[$i getMaster] getName] ne "TAPCELL_ASAP7_75t_R"} {continue}
 set bbox [$i getBBox]
 set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 if {[$bbox xMin] >= 270*$dbu && [$bbox xMax] <= 570*$dbu && [$bbox yMin] >= 336.96*$dbu && [$bbox yMax] <= 388.8*$dbu} {incr seam}
 puts $f [join [list TAP [$i getName] [[$i getMaster] getName] {*}[$i getLocation] [$i getOrient] [$i getPlacementStatus]] "\t"]
 incr taps
}
close $f
puts "OV_FRESH rows=[llength [$b getRows]] taps=$taps fully_inside_seam=$seam"
if {$seam != 0} {error "PRE hard blockage did not exclude taps from seam"}
