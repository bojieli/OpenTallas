# W18 channel hook (w18_chan_c12m9s450): flanks = neighbouring ROM clusters (M1-M7 obstructed, no cells)
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set ::ot_dbu [$tech getDbUnitsPerMicron]
proc um {v} { return [expr {round($v * $::ot_dbu)}] }
set fi [$block findInst u_flank_s]
$fi setPlacementStatus PLACED
$fi setOrient R0
$fi setLocation [um 60.0] [um 1.08]
$fi setPlacementStatus FIRM
set fi [$block findInst u_flank_n]
$fi setPlacementStatus PLACED
$fi setOrient R0
$fi setLocation [um 60.0] [um 183.6]
$fi setPlacementStatus FIRM
