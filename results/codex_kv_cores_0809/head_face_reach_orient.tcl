# S-face c_in and lt_in capture bank floorplan (0 added cycles).
# SOURCE_FRONT is the unchanged generated frontq instance name.
# Relocate the WHOLE related input-control bank coherently, preserving pin
# geometry and matching the target row orientation BEFORE setting location.
set kv_b [ord::get_db_block];set kv_u [$kv_b getDbUnitsPerMicron]
set kv_orient {}
foreach r [$kv_b getRows] {dict set kv_orient [lindex [$r getOrigin] 1] [$r getOrient]}
proc kv_face_site {i x y u orient} {
 set ux [expr {int(round($x*$u))}];set uy [expr {int(round($y*$u))}]
 if {![dict exists $orient $uy]} {error "capture target has no legal row $uy"}
 $i setPlacementStatus PLACED
 $i setOrient [dict get $orient $uy]
 $i setLocation $ux $uy
 $i setPlacementStatus FIRM
}
for {set bit 0} {$bit<4} {incr bit} {
 set suffix [expr {$bit==0?"P":"PN0"}]
 set n [format {%s.c2\[%d\]$_DFF_%s_} $SOURCE_FRONT $bit $suffix]
 set i [$kv_b findInst $n];if {$i eq "NULL"} {error "missing c_in capture $n"}
 kv_face_site $i 16.2 [expr {16.2+$bit*0.54}] $kv_u $kv_orient
}
for {set bit 0} {$bit<12} {incr bit} {
 set n [format {%s.lt2\[%d\]$_DFF_PN0_} $SOURCE_FRONT $bit]
 set i [$kv_b findInst $n];if {$i eq "NULL"} {error "missing lt_in capture $n"}
 kv_face_site $i 16.2 [expr {18.36+$bit*0.54}] $kv_u $kv_orient
}
puts "KV_FACE_CONTROL_BANK $SOURCE_FRONT 16 captures, target-row orientation, no pin/cycle change"
