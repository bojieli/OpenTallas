# Full-shape 18-SRAM port: six rows of three macros, 24um channels,
# surrounded by clear pin corridors in the 480x540um successor outline.
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set macros {}
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getType] eq "BLOCK"} { lappend macros [$inst getName] }
}
set macros [lsort -dictionary $macros]
if {[llength $macros] != 18} { error "hcoll interior requires exactly 18 SRAMs; found [llength $macros]" }
set die [$block getDieArea]
set dw [expr {double([$die dx])/$units}]
set dh [expr {double([$die dy])/$units}]
set mw 94.824
set mh 41.040
set gap 24.0
set array_w [expr {3*$mw+2*$gap}]
set array_h [expr {6*$mh+5*$gap}]
set x0 [expr {($dw-$array_w)/2}]
set y0 [expr {($dh-$array_h)/2}]
if {$x0 < 48 || $y0 < 48} { error "hcoll interior outline too small for 48um pin corridors" }
set i 0
foreach name $macros {
    set inst [$block findInst $name]
    set master [$inst getMaster]
    if {abs(double([$master getWidth])/$units-$mw)>0.01 || abs(double([$master getHeight])/$units-$mh)>0.01} {
        error "hcoll unexpected macro dimensions for $name"
    }
    set x [expr {$x0+($i%3)*($mw+$gap)}]
    set y [expr {$y0+($i/3)*($mh+$gap)}]
    # RTL macro placement locks its result; explicitly unlock before moving.
    $inst setPlacementStatus PLACED
    $inst setOrient R0
    $inst setLocation [expr {int(round($x*$units))}] [expr {int(round($y*$units))}]
    $inst setPlacementStatus FIRM
    puts "HCOLL_INTERIOR $name $x $y R0"
    incr i
}
