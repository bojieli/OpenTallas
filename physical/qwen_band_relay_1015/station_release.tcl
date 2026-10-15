# q15 r13 BAND relay: POST_GLOBAL_PLACE -- release the FIRM station flops (station_place.tcl) for resize / DPL
set ot_b [ord::get_db_block]; set ot_n 0
foreach i [$ot_b getInsts] {
  set nm [string map {\\ {}} [$i getName]]
  if {![regexp {g_lane\[\d+\]\.(tw|ty|tt|c|pw|st)_s[12]\[\d+\]} $nm]} continue
  if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED; incr ot_n }
}
puts "OT_BAND_STATIONS released $ot_n station flops"
