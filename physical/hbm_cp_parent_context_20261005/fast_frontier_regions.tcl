# FAST source e0e05a19e: explicit finite resize, not utilization relaxation.
# New source floorplan core17.28,17.28..64.8,64.8; DIE0..82.08 square.
set b [ord::get_db_block]
if {[$b getDbUnitsPerMicron] != 1000} {error "CP expected native1000DBU"}
set ca [$b getCoreArea]
if {[list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]] ne {17280 17280 64800 64800}} {error "FAST requires explicit47.52um core; do not apply to live R3"}
set body [$b findRegion cp_body]
set assoc [$b findRegion cp_association]
if {$body eq "NULL" || $assoc eq "NULL"} {error "Source-owned CP regions required"}
foreach z [$assoc getBoundaries] {
 if {[list [$z xMin] [$z yMin] [$z xMax] [$z yMax]] ne {17280 56160 22464 60480}} {error "Association boundary changed"}
}
foreach z [$body getBoundaries] {odb::dbBox_destroy $z}
foreach box {{17280 17280 60480 56160} {22464 56160 60480 60480} {60480 17280 64800 64800} {17280 60480 60480 64800}} {odb::dbBox_create $body {*}$box}
puts "OT_FAST_BODY finite_um2=2235.75552 cap50pct=1117.87776"
# Existing source-owned ancestry hook must run before each DPL, CTS and GRT.
