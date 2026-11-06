# Clock-construction correction only. Source is immutable routed Q3 A/B.
# Keep the exact BPin and all endpoint/cell/net connectivity. Complete its M5 T
# union to a rectangle; the following ordinary data ECO takes a NEW clock freeze.
read_db $::env(Q3_SOURCE_ODB)
source $::env(Q3_CLK_FREEZE_TCL)
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 1000} {error "unexpected DBU"}
set net [$block findNet clk]
set bt [$block findBTerm clk]
set port_boxes {}
foreach p [$bt getBPins] {foreach b [$p getBoxes] {
 lappend port_boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}}
if {$port_boxes ne {{M5 276000 168456 276480 168504}}} {error "unexpected Q3 clk BPin: $port_boxes"}
set before [ot_clk_wire_ops $net]
set body {};set properties {}
foreach a $before {
 if {[lindex $a 0] eq "wireProperty"} {lappend properties [lrange $a 1 2]} else {lappend body $a}
}
set found 0
foreach a $body {
 if {[lindex $a 0] eq "addPoint" && [lrange $a 1 2] eq {276120 168480}} {incr found}
}
if {$found != 1} {error "expected one measured clock access point, got $found"}
set layer [[[$block getDb] getTech] findLayer M5]
# Append, so EVERY existing junction/property index remains unchanged.
set extra [list [list newPath $layer FIXED] {addPoint 276120 168480} {addRect -144 -24 360 480}]
set expected [concat $body $extra]
set nw [odb::dbWire_create $block];set enc [odb::dbWireEncoder];$enc begin $nw
foreach a $expected {$enc {*}$a}
$enc end
foreach pair $properties {
 lassign $pair j p
 if {![$nw setProperty $j $p]} {error "cannot preserve old wire property $j"}
}
set old [$net getWire];odb::dbWire_destroy $old;$nw attach $net
set after_body {}
foreach a [ot_clk_wire_ops $net] {if {[lindex $a 0] ne "wireProperty"} {lappend after_body $a}}
if {$after_body ne $expected} {error "clock geometry does not match original plus exact rectangle"}
set after_boxes {}
foreach p [$bt getBPins] {foreach b [$p getBoxes] {
 lappend after_boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}}
if {$after_boxes ne $port_boxes} {error "BPin changed"}
write_db $::env(Q3_OUTPUT_ODB)
puts "Q3_CLOCK_RECTANGLE PASS: clk-only M5 rectangle275976,168456..276480,168960nm; exact original wire operations retained, BPin unchanged, no cell/net/endpoint/phase/RTL/cycle changes"
