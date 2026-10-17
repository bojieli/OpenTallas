# Place a scalar BTerm at a GRANTED along-face centre, without place_pin's
# coordinate/shape-offset snapping. The caller must supply a legal actual
# routing-track centre. This helper never changes or repairs a grant.
#
# Usage: source this file, then
#   ot_assigned_pin_exact {data[0]} M5 N 178.188
# Face is N/S/E/W and centre is microns along X for N/S, Y for E/W.
# Existing legal pin dimensions are preserved. For an unplaced BTerm only,
# place_pin seeds its ordinary dimensions; its resulting location is discarded.
# PG BTerms are never removed. The enclosing kit must audit signal spacing,
# PG clearance, all assigned centres and complete port coverage after placement.
proc ot_assigned_pin_exact {name layer face center_um} {
    if {$face ni {N S E W}} {error "ASSIGNED_PIN_EXACT invalid face $face"}
    set block [ord::get_db_block]
    set tech [ord::get_db_tech]
    set units [$block getDbUnitsPerMicron]
    set bt [$block findBTerm $name]
    if {$bt eq "" || $bt eq "NULL"} {error "ASSIGNED_PIN_EXACT missing BTerm $name"}
    if {[$bt getSigType] in {POWER GROUND}} {error "ASSIGNED_PIN_EXACT refuses PG BTerm $name"}
    set tl [$tech findLayer $layer]
    if {$tl eq "" || $tl eq "NULL"} {error "ASSIGNED_PIN_EXACT missing layer $layer"}
    set grid [$block findTrackGrid $tl]
    if {$grid eq "" || $grid eq "NULL"} {error "ASSIGNED_PIN_EXACT no actual track grid for $layer"}
    set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
    set target [expr {double($center_um)*$units}]
    set target_int [expr {int(round($target))}]
    if {abs($target-$target_int)>0.0001 || [lsearch -exact $tracks $target_int]<0} {
        error "ASSIGNED_PIN_EXACT $name grant $center_um is not on actual $layer $face track"
    }
    set die [$block getDieArea]
    set lo [expr {$face in {N S}?[$die xMin]:[$die yMin]}]
    set hi [expr {$face in {N S}?[$die xMax]:[$die yMax]}]
    if {$target<=$lo || $target>=$hi} {error "ASSIGNED_PIN_EXACT $name outside face extent"}
    set seeded [expr {[llength [$bt getBPins]]==0}]
    if {$seeded} {
        set x [expr {$face eq "W"?[$die xMin]/double($units):($face eq "E"?[$die xMax]/double($units):$center_um)}]
        set y [expr {$face eq "S"?[$die yMin]/double($units):($face eq "N"?[$die yMax]/double($units):$center_um)}]
        place_pin -pin_name $name -layer $layer -location [list $x $y] -force_to_die_boundary
    }
    set pins [$bt getBPins]
    if {[llength $pins]!=1 || [llength [[lindex $pins 0] getBoxes]]!=1} {
        error "ASSIGNED_PIN_EXACT $name needs one ordinary rectangular seed pin"
    }
    set old [lindex [[lindex $pins 0] getBoxes] 0]
    set seed_center [expr {$face in {N S}?([$old xMin]+[$old xMax])/2.0:([$old yMin]+[$old yMax])/2.0}]
    if {[[$old getTechLayer] getName] ne $layer} {error "ASSIGNED_PIN_EXACT $name seed layer differs from grant"}
    set width [expr {[$old xMax]-[$old xMin]}]
    set height [expr {[$old yMax]-[$old yMin]}]
    if {$face in {N S}} {
        set x0 [expr {$target-$width/2.0}]
        set y0 [expr {$face eq "S"?[$die yMin]:[$die yMax]-$height}]
    } else {
        set x0 [expr {$face eq "W"?[$die xMin]:[$die xMax]-$width}]
        set y0 [expr {$target-$height/2.0}]
    }
    if {abs($x0-round($x0))>0.0001 || abs($y0-round($y0))>0.0001} {
        error "ASSIGNED_PIN_EXACT $name seed shape cannot be centred exactly on granted DBU coordinate"
    }
    set x0 [expr {int(round($x0))}];set y0 [expr {int(round($y0))}]
    foreach bp $pins {odb::dbBPin_destroy $bp}
    set pin [odb::dbBPin_create $bt]
    $pin setPlacementStatus FIRM
    odb::dbBox_create $pin $tl $x0 $y0 [expr {$x0+$width}] [expr {$y0+$height}]
    set actual [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
    set got [expr {$face in {N S}?([$actual xMin]+[$actual xMax])/2.0:([$actual yMin]+[$actual yMax])/2.0}]
    if {abs($got-$target)>0.0001 || [[$actual getTechLayer] getName] ne $layer ||
        [$actual xMax]-[$actual xMin]!=$width || [$actual yMax]-[$actual yMin]!=$height} {
        error "ASSIGNED_PIN_EXACT actual ODB rectangle differs from grant for $name"
    }
    return [dict create pin $name face $face layer $layer center_um [expr {$got/double($units)}] width_dbu $width height_dbu $height seeded $seeded seed_center_um [expr {$seed_center/double($units)}]]
}
