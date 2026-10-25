# Co-locate the existing snapshot/offset/onehot pipeline; no RTL or data edits.
uplevel #0 {
set r_blk [ord::get_db_block]
set r_u [[ord::get_db_tech] getDbUnitsPerMicron]
set r_off {}; set r_snap {}
foreach i [$r_blk getInsts] {
 set n [string map [list [format %c 92] ""] [$i getName]]
 if {[regexp {^c1_off\[([0-9]+)\]\$_DFF_P_$} $n -> k]} {dict set r_off $k $i}
 if {[regexp {^g_rs1\.u_rs/q\[([0-9]+)\]\$_DFF_P_$} $n -> k] && $k>0} {dict set r_snap [expr {$k-1}] $i}
}
if {[dict size $r_off]!=24 || [dict size $r_snap]!=24} {error "RP1_SNAPSHOT expected24 offset and24 input snapshot FFs"}
dict for {k i} $r_snap {
 lassign [[dict get $r_off $k] getLocation] x y
 $i setPlacementStatus PLACED
 $i setLocation $x [expr {$y+int(0.54*$r_u)}]
}
detailed_placement
check_placement -verbose
puts "RP1_SNAPSHOT PASS placed24 existing_input_registers data_changes0 added_cycles0"
}
