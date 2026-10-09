# Fullshape64macros.40FN +24BF16 macros.
# Interior40um corridors, macros200um from pins; no pin edge obstruction.
set db [ord::get_db]
set block [ord::get_db_block]
set macros [list]
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2"} {lappend macros $inst}
}
if {[llength $macros] != 64} {error "HC fullshape requires64 SRAMs, found [llength $macros]"}
set i 0
foreach inst $macros {
 set x [expr {200.0 + ($i % 8) * 125.0}]
 set y [expr {200.0 + ($i / 8) * 82.0}]
 $inst setOrient R0
 $inst setLocation [ord::microns_to_dbu $x] [ord::microns_to_dbu $y]
 $inst setPlacementStatus FIRM
 incr i
}
