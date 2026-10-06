# R3 measured 868.99716um2 body plus late ungrouped repair exceeds 839.808um2.
# Add the previously unused upper-right part of the SAME 43.2um core.
# Association, pins, PG, rows, clock, padding and utilization policy stay fixed.
set ot_b [ord::get_db_block]
if {[$ot_b getDbUnitsPerMicron]!=1000} {error "CP R3 hook requires actual1000DBU grid"}
set ot_r [$ot_b findRegion cp_body]
set ot_a [$ot_b findRegion cp_association]
if {$ot_r eq "NULL" || $ot_a eq "NULL"} {error "Missing finite CP body/association"}
set ot_original 0;set ot_present 0
foreach ot_box [$ot_r getBoundaries] {
 set ot_coords [list [$ot_box xMin] [$ot_box yMin] [$ot_box xMax] [$ot_box yMax]]
 if {$ot_coords eq {17280 17280 60480 56160}} {set ot_original 1}
 if {$ot_coords eq {22464 56160 60480 60480}} {set ot_present 1}
 if {$ot_coords ni {{17280 17280 60480 56160} {22464 56160 60480 60480}}} {error "Unexpected CP body geometry $ot_coords"}
}
if {!$ot_original} {error "Original measured CP body missing"}
foreach ot_box [$ot_a getBoundaries] {
 if {[list [$ot_box xMin] [$ot_box yMin] [$ot_box xMax] [$ot_box yMax]] ne {17280 56160 22464 60480}} {error "Association geometry changed"}
}
if {!$ot_present} {odb::dbBox_create $ot_r 22464 56160 60480 60480}
puts "OT_CP_R3_FINITE_BODY outline_um2=1843.84512 cell_cap_at50pct=921.92256"
# Before native DPL, caller invokes existing actual ancestry membership hook.
