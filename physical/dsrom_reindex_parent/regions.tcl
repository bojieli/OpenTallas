# Fence all control/consumer/request cells to the original fixed control slot.
# Only the actual list-memory frontend is beside its newly priced macro array.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
proc region {block dbu name x0 y0 x1 y1} {
    set r [odb::dbRegion_create $block $name]
    $r setRegionType EXCLUSIVE
    odb::dbBox_create $r [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
    set g [odb::dbGroup_create $block $name]
    $r addGroup $g
    return $g
}
set control [region $block $dbu reindex_control 2.052 2.160 308.124 308.070]
set memory [region $block $dbu reindex_list 2.052 312.324 726.324 458.910]
set nc 0;set nm 0
foreach inst [$block getInsts] {
    if {[[$inst getMaster] isBlock]} {continue}
    if {[string match *u_control.u_list* [$inst getName]]} {$memory addInst $inst;incr nm} else {$control addInst $inst;incr nc}
}
if {$nc==0 || $nm==0} {error "missing actual control/list members nc=$nc nm=$nm"}
puts "REINDEX_FIXED_REGIONS control_cells=$nc list_cells=$nm cap_um2=37452.2"
