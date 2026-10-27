# Integration test against a real saved ODB, not a simulated database.
# ASSIGNED_PIN_TEST_ODB, ASSIGNED_PIN_HELPER and ASSIGNED_PIN_TEST_OUT are paths.
read_db $::env(ASSIGNED_PIN_TEST_ODB)
source $::env(ASSIGNED_PIN_HELPER)
set b [ord::get_db_block]
set t [ord::get_db_tech]
set u [$b getDbUnitsPerMicron]
set die [$b getDieArea]
foreach item {{M4 Y} {M5 X}} {
    lassign $item layer axis
    set grid [$b findTrackGrid [$t findLayer $layer]]
    set positions [expr {$axis eq "X"?[$grid getGridX]:[$grid getGridY]}]
    puts "ASSIGNED_PIN_TRACK_GRID layer=$layer axis=$axis first_dbu=[lindex $positions 0] next_dbu=[lindex $positions 1] last_dbu=[lindex $positions end] count=[llength $positions] units=$u spacing_dbu=[[$t findLayer $layer] getSpacing]"
}
set selected {}
set per_face [dict create N 0 S 0 E 0 W 0]
foreach bt [$b getBTerms] {
    if {[$bt getSigType] in {POWER GROUND} || [llength [$bt getBPins]]!=1} continue
    set boxes [[lindex [$bt getBPins] 0] getBoxes]
    if {[llength $boxes]!=1} continue
    set box [lindex $boxes 0]
    set x [expr {([$box xMin]+[$box xMax])/2.0}]
    set y [expr {([$box yMin]+[$box yMax])/2.0}]
    set sides [list [list [expr {abs($x-[$die xMin])}] W] [list [expr {abs($x-[$die xMax])}] E] [list [expr {abs($y-[$die yMin])}] S] [list [expr {abs($y-[$die yMax])}] N]]
    set face [lindex [lindex [lsort -real -index 0 $sides] 0] 1]
    if {[dict get $per_face $face]>=3} continue
    set layer [[$box getTechLayer] getName]
    set grid [$b findTrackGrid [$t findLayer $layer]]
    set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
    set along [expr {$face in {N S}?$x:$y}]
    if {[lsearch -exact $tracks [expr {int(round($along))}]]<0} continue
    lappend selected [list [$bt getName] $face $layer $along [expr {[$box xMax]-[$box xMin]}] [expr {[$box yMax]-[$box yMin]}]]
    dict incr per_face $face
}
foreach face {N S E W} {if {[dict get $per_face $face]<1} {error "test fixture has no ordinary on-track $face pin"}}
set records [open $::env(ASSIGNED_PIN_TEST_OUT) w]
puts $records "pin\tface\tlayer\tgranted_dbu\tillegal_request_dbu\tplace_pin_actual_dbu\texact_actual_dbu\twidth_dbu\theight_dbu"
set reproduced 0
set legal_displacements 0
set cached_seed_displacements 0
set negatives 0
set checked 0
foreach item $selected {
    lassign $item name face layer target width height
    set bt [$b findBTerm $name]
    foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
    set um [expr {$target/double($u)}]
    set x [expr {$face eq "W"?[$die xMin]/double($u):($face eq "E"?[$die xMax]/double($u):$um)}]
    set y [expr {$face eq "S"?[$die yMin]/double($u):($face eq "N"?[$die yMax]/double($u):$um)}]
    place_pin -pin_name $name -layer $layer -location [list $x $y] -force_to_die_boundary
    set old [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
    set legal_before [expr {$face in {N S}?([$old xMin]+[$old xMax])/2.0:([$old yMin]+[$old yMax])/2.0}]
    if {$legal_before!=$target} {incr legal_displacements}
    # A physical grant on a non-track coordinate must be rejected, rather
    # than silently adopting the nearest coordinate returned by place_pin.
    foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
    set illegal_um [expr {$um+1.0/$u}]
    set illegal_x [expr {$face in {N S}?$illegal_um:$x}]
    set illegal_y [expr {$face in {E W}?$illegal_um:$y}]
    place_pin -pin_name $name -layer $layer -location [list $illegal_x $illegal_y] -force_to_die_boundary
    set old [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
    set before [expr {$face in {N S}?([$old xMin]+[$old xMax])/2.0:([$old yMin]+[$old yMax])/2.0}]
    if {$before!=$target+1} {incr reproduced}
    set result [ot_assigned_pin_exact $name $layer $face $um]
    # Independent readback of the new ODB shape, plus idempotence.
    ot_assigned_pin_exact $name $layer $face $um
    # Also exercise an unplaced BTerm: ordinary shape seeding may snap,
    # but the final assigned centre must still be exact.
    foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
    set seed_result [ot_assigned_pin_exact $name $layer $face $um]
    if {abs([dict get $seed_result seed_center_um]-$um)>0.0001} {incr cached_seed_displacements}
    set after [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
    set actual [expr {$face in {N S}?([$after xMin]+[$after xMax])/2.0:([$after yMin]+[$after yMax])/2.0}]
    if {$actual!=$target || [$after xMax]-[$after xMin]!=$width || [$after yMax]-[$after yMin]!=$height} {
        error "integration test: exact centre/seed shape failed on $name"
    }
    if {![catch {ot_assigned_pin_exact $name $layer $face [expr {$um+1.0/$u}]} message] || ![string match {*not on actual*} $message]} {
        error "off-track grant was accepted for $name"
    }
    incr negatives
    puts $records "$name\t$face\t$layer\t$target\t[expr {$target+1}]\t$before\t$actual\t$width\t$height"
    incr checked
}
foreach bt [$b getBTerms] {
    if {[$bt getSigType] in {POWER GROUND}} {
        if {![catch {ot_assigned_pin_exact [$bt getName] M5 N 1.0} message] || ![string match {*refuses PG*} $message]} {error "PG mutation guard failed"}
        incr negatives;break
    }
}
close $records
if {$reproduced==0} {error "fixture did not reproduce silent snapping of an illegal requested centre"}
puts "ASSIGNED_PIN_EXACT_TEST PASS checked=$checked faces=$per_face illegal_requests_snapped=$reproduced first_legal_target_displacements=$legal_displacements cached_seed_displacements=$cached_seed_displacements negative_guards=$negatives unplaced_seed_cases=$checked"
