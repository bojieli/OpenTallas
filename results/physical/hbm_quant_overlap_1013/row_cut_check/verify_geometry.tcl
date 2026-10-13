read_db $::env(OV_FRESH_DB)
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rows_inside 0; set taps_overlap 0; set boundary_caps 0
foreach r [$b getRows] {
 set a [$r getBBox]
 if {[$a xMax] > 270*$dbu && [$a xMin] < 570*$dbu && [$a yMax] > 336.96*$dbu && [$a yMin] < 388.8*$dbu} {incr rows_inside}
}
foreach i [$b getInsts] {
 if {[[$i getMaster] getName] ne "TAPCELL_ASAP7_75t_R"} {continue}
 set a [$i getBBox]
 if {[$a xMax] > 270*$dbu && [$a xMin] < 570*$dbu && [$a yMax] > 336.96*$dbu && [$a yMin] < 388.8*$dbu} {incr taps_overlap}
 if {[$a yMin] >= 336.96*$dbu && [$a yMax] <= 388.8*$dbu &&
     (abs([$a xMax]-270*$dbu)<1 || abs([$a xMin]-570.024*$dbu)<1)} {incr boundary_caps}
}
puts "OV_BOUNDARY intersecting_rows=$rows_inside any_intersecting_tap_caps=$taps_overlap seam_boundary_caps=$boundary_caps"
if {$rows_inside !=0 || $taps_overlap !=0 || $boundary_caps ==0} {error "seam geometry guard failed"}
