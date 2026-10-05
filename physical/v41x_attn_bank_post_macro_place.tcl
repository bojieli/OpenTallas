# Keep the macro's data-pin edge away from the core perimeter. The generated
# ASAP7 LEF places all 256 read and 256 write pins on its local left edge.
# RTLMP otherwise puts that edge ~3 um from the core boundary, leaving no
# useful standard-cell channel for the registered interface.
set mem [[ord::get_db_block] findInst u_mem]
$mem setPlacementStatus PLACED
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
$mem setLocation [expr {round(44.0 * $dbu)}] [expr {round(44.0 * $dbu)}]
$mem setPlacementStatus LOCKED
