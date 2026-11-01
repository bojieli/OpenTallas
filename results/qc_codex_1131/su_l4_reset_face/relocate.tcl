set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /origin/macros/*_tt.lib] {read_liberty $f}
set base /origin/run/results/asap7/kq_qfd_qc_su_lane_w_l4_wd7e00f/base
read_db $base/3_place.odb
read_sdc $base/3_place.sdc
source /origin/setRC_rcx.tcl
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set before [llength [$b getInsts]]
set f [open /work/reset_moves.tsv w]
puts $f "instance\tmaster\tbefore_x\tbefore_y\tafter_x\tafter_y"
set moves [list [list {wire19706} 207.36 10.8] [list {u_u_rsq4.rt$_DFF_PN0_} 204.552 17.28] [list {u_u_lrly4.u_rlz.rs1$_DFF_P_} 207.36 17.28] [list {u_u_head4.u_h.u_rland/s\[0\]$_DFF_P_} 210.168 17.28]]
foreach row $moves {
 lassign $row n x y
 set i [$b findInst $n]
 if {$i eq "NULL"} {error "RESET_FACE missing exact source cell $n"}
 set master [$i getMaster]
 if {[$master isBlock]} {error "RESET_FACE refuses macro $n"}
 set old [$i getLocation]
 set ty [expr {round($y*$dbu)}]
 set found 0
 foreach r [$b getRows] {
  lassign [$r getOrigin] rx ry
  if {$ry == $ty} {$i setOrient [$r getOrient]; set found 1; break}
 }
 if {!$found} {error "RESET_FACE target y has no physical row: $n $y"}
 $i setLocation [expr {round($x*$dbu)}] $ty
 $i setPlacementStatus FIRM
 lassign $old ox oy
 puts $f "$n\t[$master getName]\t[expr {$ox/double($dbu)}]\t[expr {$oy/double($dbu)}]\t$x\t$y"
}
close $f
detailed_placement
check_placement -verbose
if {[llength [$b getInsts]] != $before} {error "RESET_FACE unexpected cell inventory change"}
write_db /work/3_reset_face.odb
write_sdc /work/3_reset_face.sdc
puts "RESET_FACE_PLACED same RTL/netlist/cell inventory; four exact existing instances relocated; actual DPL legal"
