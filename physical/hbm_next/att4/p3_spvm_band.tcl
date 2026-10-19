# Confine shared decode, arithmetic and return logic to one FULL-WIDTH (core edge to core edge) central standard-cell band (safe checklist 6; was 54-378 um, LH-P3UNITS 10-19).
# OpenDB API: https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/db.h (dbRegion).
set hnx_block [ord::get_db_block]
set hnx_dbu [$hnx_block getDbUnitsPerMicron]
set hnx_region [$hnx_block findRegion hnx_p3_common]
if {$hnx_region eq "NULL"} {
    set hnx_region [odb::dbRegion_create $hnx_block hnx_p3_common]
    # OpenDB region types are INCLUSIVE/EXCLUSIVE; EXCLUSIVE is the DEF FENCE type ("FENCE" raised
    # "Unknown region type" at 3_3_place_gp in gates 080811/081811).
    $hnx_region setRegionType EXCLUSIVE
    odb::dbBox_create $hnx_region [expr {round(2.16*$hnx_dbu)}] [expr {round(183.6*$hnx_dbu)}] [expr {round(429.84*$hnx_dbu)}] [expr {round(248.4*$hnx_dbu)}]
}
set hnx_group [$hnx_block findGroup hnx_p3_common]
if {$hnx_group eq "NULL"} {set hnx_group [odb::dbGroup_create $hnx_region hnx_p3_common]}
set hnx_count 0
foreach hnx_inst [$hnx_block getInsts] {
    if {[[$hnx_inst getMaster] isBlock] || [$hnx_inst isFixed]} {continue}
    if {[string first "u_sm" [$hnx_inst getName]] < 0} {continue}
    $hnx_group addInst $hnx_inst
    incr hnx_count
}
if {$hnx_count < 100} {error "HNEXT P3 common band matched only $hnx_count cells"}
puts "HNEXT P3 common band: $hnx_count cells, full core width 427.68 x 64.8um (y 183.6-248.4); macro arrays above/below"
