# Private coupon row mask: six complete legal rows, no cell placement.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set lo [expr {round(20.79*$dbu)}]
set hi [expr {round(22.41*$dbu)}]
foreach row [$block getRows] {
 set bb [$row getBBox]
 if {[$bb yMin] < $lo || [$bb yMax] > $hi} {odb::dbRow_destroy $row}
}
if {[llength [$block getRows]] != 6} {error "coupon expected exactly six full-width .27um rows"}
