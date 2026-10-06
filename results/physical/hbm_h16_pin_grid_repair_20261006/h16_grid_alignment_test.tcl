read_db /checkpoint/4_cts.odb
set b [ord::get_db_block]
set ly [[ord::get_db_tech] findLayer M4]
set g [$b findTrackGrid $ly]
set ys [$g getGridY]
set start [lindex $ys 0]
set pitch [expr {[lindex $ys 1]-$start}]
if {$start!=12 || $pitch!=48} {error "Unexpected actual M4 track phase"}
set n 0
foreach i [$b getInsts] {
 if {[[$i getMaster] getName] ne "ot_attn_hgrp_m6h1"} {continue}
 if {[$i getOrient] ne "R0"} {error "Unexpected headorientation"}
 lassign [$i getOrigin] x y
 set ny [expr {int(ceil(double($y)/48))*48}]
 if {$ny-$y<0 || $ny-$y>47} {error "Unbounded alignment shift"}
 set old_status [$i getPlacementStatus]
 $i setPlacementStatus PLACED
 $i setOrigin $x $ny
 $i setPlacementStatus $old_status
 puts "OT_HEAD_NATIVE_GRID [$i getName] origin=$x,$y -> $x,$ny shift_y_DBU=[expr {$ny-$y}]"
 incr n
}
if {$n!=16} {error "Requires actual16 heads"}
write_db /output/m4_aligned_copy.odb
set_routing_layers -signal M2-M9
pin_access
puts OT_H16_ALIGNED_NATIVE_PIN_ACCESS_PASS
