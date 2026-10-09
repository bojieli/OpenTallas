# Enumerate the actual OpenDB instances: frontend escaping of generated hierarchy names
# differs between the synthesis Verilog and the linked DB. Placement never guesses names.
set crom_block [ord::get_db_block]
set crom_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set crom_macros {}
foreach m [$crom_block getInsts] {
 if {[[$m getMaster] isBlock] && [[$m getMaster] getName] eq "ot_rom_4096x266_m8"} {
  lappend crom_macros [$m getName]
 }
}
if {[llength $crom_macros] != 48} {error "CROM48 requires48 real macros; found [llength $crom_macros]"}
set crom_i 0
foreach name [lsort -dictionary $crom_macros] {
 set m [$crom_block findInst $name]
 set x [expr {12.96+($crom_i%4)*190.0}]
 set y [expr {12.96+($crom_i/4)*80.0}]
 $m setOrient R0
 $m setLocation [expr {round($x*$crom_dbu)}] [expr {round($y*$crom_dbu)}]
 $m setPlacementStatus FIRM
 puts "CROM48 macro $name at $x $y"
 incr crom_i
}
