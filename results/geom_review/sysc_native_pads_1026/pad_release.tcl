uplevel #0 {
set b [ord::get_db_block]
foreach i [$b getInsts] { if {[regexp {^u_bound[.]u_pd[0-9]+_} [$i getName]] && [$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED } }
}
