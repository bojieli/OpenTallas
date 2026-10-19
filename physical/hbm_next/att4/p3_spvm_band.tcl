# Confine shared decode, arithmetic and return logic to one full-width central standard-cell band.
# OpenDB API: https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/db.h (dbRegion).
set hnx_block [ord::get_db_block]
set hnx_dbu [$hnx_block getDbUnitsPerMicron]
set hnx_region [$hnx_block findRegion hnx_p3_common]
if {$hnx_region eq "NULL"} {
    set hnx_region [odb::dbRegion_create $hnx_block hnx_p3_common]
    $hnx_region setRegionType FENCE
    odb::dbBox_create $hnx_region [expr {round(54.0*$hnx_dbu)}] [expr {round(183.6*$hnx_dbu)}] [expr {round(378.0*$hnx_dbu)}] [expr {round(248.4*$hnx_dbu)}]
}
set hnx_count 0
foreach hnx_inst [$hnx_block getInsts] {
    if {[[$hnx_inst getMaster] isBlock] || [$hnx_inst isFixed]} {continue}
    if {[string first "u_sm" [$hnx_inst getName]] < 0} {continue}
    $hnx_region addInst $hnx_inst
    incr hnx_count
}
if {$hnx_count < 100} {error "HNEXT P3 common band matched only $hnx_count cells"}
puts "HNEXT P3 common band: $hnx_count cells, 324 x64.8um; macro arrays above/below"
