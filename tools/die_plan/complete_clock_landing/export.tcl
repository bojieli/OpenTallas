source /out/clk_freeze.tcl
read_db /out/clock_component_routed.odb
set result {};set drivers {}
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] ne "CLOCK"} continue
 if {[llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {error "not component two-terminal"}
 set driver [lindex [$net getITerms] 0]; set inst [$driver getInst]
 dict set drivers [$net getName] [list [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [[$driver getMTerm] getName]]
 set out {}
 foreach op [ot_clk_wire_ops $net] {
  switch [lindex $op 0] {
   newPath {
    set layer [lindex $op 1]
    if {[string is integer -strict $layer] || [llength $op] != 3} {error "unsupported junction or NDR"}
    lappend out [list PATH [$layer getName]]
   }
   addPoint - addRect {lappend out $op}
   addTechVia {lappend out [list TVIA [[lindex $op 1] getName]]}
   addITerm {if {[lindex $op 1] ne $driver} {error "unexpected routed driver ITerm"}; lappend out [list ITERM [[$driver getInst] getName] [[$driver getMTerm] getName]]}
   addBTerm {if {![string match __ot_land_* [[lindex $op 1] getName]]} {error "unexpected BTerm"}}
   default {error "unsupported component wire operation $op"}
  }
 }
 dict set result [$net getName] $out
}
if {[dict size $result] != $::env(OT_LANDING_COUNT)} {error "expected declared count"}
set f [open /out/component_ops.tcl w]
puts $f [list set ::component_ops $result]
puts $f [list set ::component_drivers $drivers]
close $f
puts "COMPONENT_OPS [dict size $result] actual native complete driver routes"
