read_db /work/run/results/asap7/dp_hd_spn/base/3_place.preshift.odb
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
set dy [expr {round(34.56*$dbu)}]
if {$dy % [expr {round(0.54*$dbu)}] || $dy % [expr {round(8.64*$dbu)}]} { error "shift changed native row or PG grid phase" }
set moved 0
foreach i [$blk getInsts] {
 if {![string match {u_cland_x_i/*} [$i getName]]} continue
 set mn [[$i getMaster] getName]
 if {$mn ni {DFFHQNx1_ASAP7_75t_R DFFLQNx1_ASAP7_75t_R}} continue
 lassign [$i getLocation] x y
 $i setPlacementStatus PLACED
 $i setLocation $x [expr {$y+$dy}]
 $i setPlacementStatus FIRM
 incr moved
}
if {$moved != 2941} { error "unexpected moved ring FF count: $moved" }
puts "SPN_BAND_SHIFT moved $moved dy_um 34.56 native_rows 128 PG_periods 4; before CTS"
detailed_placement
check_placement -verbose
write_db /work/run/results/asap7/dp_hd_spn/base/3_place.odb
puts "SPN_BAND_SHIFT legal placement PASS"
