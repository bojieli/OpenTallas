# Candidate-only restoration to the complete frozen public pin-centre/layer table.
read_db /work/input.odb
set b [ord::get_db_block];set tech [ord::get_db_tech]
set expected {};set rows {};set f [open /work/public_pins.tsv r]
while {[gets $f line]>=0} {lassign [split $line "\t"] name layer x y;dict set expected $name 1;lappend rows [list $name $layer $x $y]}
close $f
foreach bt [$b getBTerms] {if {![dict exists $expected [$bt getName]] && [$bt getSigType] ni {POWER GROUND}} {error "PUBLIC_EXTRA_SIGNAL [$bt getName]"}}
set o [open /work/restored_pin_rectangles.tsv w]
puts $o "name\tlayer\tx0\ty0\tx1\ty1\tcentre_x\tcentre_y"
set count 0
foreach row $rows {
 lassign $row name layer x y
 set bt [$b findBTerm $name];if {$bt eq "NULL"} {error "PUBLIC_MISSING $name"}
 set old [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
 set w [expr {[$old xMax]-[$old xMin]}];set h [expr {[$old yMax]-[$old yMin]}]
 if {$layer ne "M4"} {error "PUBLIC_EXPECTED_M4 $name"};set w 192;set h 24
 if {$w%2 || $h%2} {error "PUBLIC_ODD_BOX $name"}
 set x0 [expr {$x-$w/2}];set y0 [expr {$y-$h/2}];set x1 [expr {$x+$w/2}];set y1 [expr {$y+$h/2}]
 if {$x0<0 || $y0<0 || $x1>457920 || $y1>1157760} {error "PUBLIC_BOX_OUTSIDE $name"}
 foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
 set bp [odb::dbBPin_create $bt];$bp setPlacementStatus FIRM
 set ly [$tech findLayer $layer];if {$ly eq "NULL"} {error "PUBLIC_LAYER $layer"}
 set box [odb::dbBox_create $bp $ly $x0 $y0 $x1 $y1]
 if {([$box xMin]+[$box xMax])!=2*$x || ([$box yMin]+[$box yMax])!=2*$y || [[$box getTechLayer] getName] ne $layer} {error "PUBLIC_RESTORE_FAILED $name"}
 puts $o "$name\t$layer\t$x0\t$y0\t$x1\t$y1\t$x\t$y";incr count
}
close $o
puts "A0_COMPLETE_PUBLIC_EDGE_PIN_RESTORE_PASS $count"
write_db /work/public_restored.odb
set ::env(OT_GEOM_OUT) /work/geom_public_restored.tsv
source /work/geom_dump.tcl
