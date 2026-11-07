# HBM-FORM-TIMING-13 rest_1c vF (PART 50 form + visual check 22:1x, smell 1 "logic far from its pins / opposite sides"):
# vD GPL pulled the 128 part-50 pipe registers u_fcore.u_core_u_vm_scalar_data[*] to (80,145) um, 400 um from their
# select sources on the E face (x 421, y 15-90) -> TT -79 on that leg.  PRE_GLOBAL_PLACE, after face_flops.tcl: place
# them FIRM in a compact 8 x 16 grid centred at OT_P50_PIPE_XY (um; default 250 95 = between the E-face sources, the
# internal mux operands and the S-face scalar_data flops at x~220), released to PLACED before DPL via ot_face_flops.txt.
uplevel #0 {
set pp_blk [ord::get_db_block]
set pp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set pp_xy [expr {[info exists ::env(OT_P50_PIPE_XY)] ? $::env(OT_P50_PIPE_XY) : "250 95"}]
lassign $pp_xy pp_cx pp_cy
set pp_regs {}
foreach i [$pp_blk getInsts] {
  if {[string match {u_fcore.u_core_u_vm_scalar_data*} [$i getName]] && [string match "*DFF*" [[$i getMaster] getName]]} { lappend pp_regs $i }
}
set pp_regs [lsort -command {apply {{a b} {
  regexp {\[(\d+)\]} [$a getName] -> ia; regexp {\[(\d+)\]} [$b getName] -> ib; expr {$ia - $ib}}}} $pp_regs]
set pp_n [llength $pp_regs]
set pp_cols 8
set pp_px [expr {3.0 * $pp_dbu}]; set pp_py [expr {1.08 * $pp_dbu}]
set pp_rows [expr {($pp_n + $pp_cols - 1) / $pp_cols}]
set pp_x0 [expr {$pp_cx * $pp_dbu - $pp_cols * $pp_px / 2.0}]; set pp_y0 [expr {$pp_cy * $pp_dbu - $pp_rows * $pp_py / 2.0}]
set pp_k 0
set fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach i $pp_regs {
  set pp_c [expr {$pp_k % $pp_cols}]; set pp_r [expr {$pp_k / $pp_cols}]
  $i setLocation [expr {int($pp_x0 + $pp_c * $pp_px)}] [expr {int($pp_y0 + $pp_r * $pp_py)}]
  $i setPlacementStatus FIRM
  puts $fh "[$i getName]\tp50pipe"
  incr pp_k
}
close $fh
puts "OT_P50_PIPE placed $pp_k part-50 pipe registers FIRM in a ${pp_cols}x${pp_rows} grid at ($pp_cx,$pp_cy) um"
}
