# Enumerate the actual OpenDB instances: frontend escaping of generated hierarchy names
# differs between the synthesis Verilog and the linked DB. Placement never guesses names.
set crom_block [ord::get_db_block]
set crom_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set crom_macros {}
foreach m [$crom_block getInsts] {
 if {[[$m getMaster] isBlock] && [[$m getMaster] getName] eq "ot_sram_1r1w_64x512_m1_r2c2"} {
  lappend crom_macros [$m getName]
 }
}
if {[llength $crom_macros] != 2} {error "QWEN_W1_TRANSIENT2 requires2 real macros; found [llength $crom_macros]"}
set crom_i 0
foreach name [lsort -dictionary $crom_macros] {
 set m [$crom_block findInst $name]
 set x [expr {12.96+($crom_i%2)*200.0}]
 set y [expr {12.96+0}]
 $m setOrient R0
 $m setLocation [expr {round($x*$crom_dbu)}] [expr {round($y*$crom_dbu)}]
 $m setPlacementStatus FIRM
 puts "QWEN_W1_TRANSIENT2 macro $name at $x $y"
 incr crom_i
}
