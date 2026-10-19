# qfd_tt_head_static_h15 (Q-TTH15 2026-10-17): keep the controller in the E "home" band (E band x >= 216.6 + SE S band
# x >= 129.6, y <= 43.2) next to the mirrored macros' read/clk edge.  15% PARTIAL placement blockages on the N band
# (above the macro stack, x < 216.6) and the SW S band (x < 129.6, y < 43.2): repeaters on the ~575 W<->E crossing bits
# still fit, the controller logic cannot smear around the stack (h14d: 17.5% density ring).  Sourced from pre_gpl.tcl
# (pin_hook_before_flops) so global placement sees them; post_resize_relocate skips partial blockages.
set ot_h15_b [ord::get_db_block]
set ot_h15_d [$ot_h15_b getDbUnitsPerMicron]
set ot_h15_die [$ot_h15_b getDieArea]
foreach {ot_h15_n ot_h15_r} [list N {0 198.768 216.6 222.48} SW_S {0 0 129.6 43.2}] {
  lassign $ot_h15_r ot_h15_x0 ot_h15_y0 ot_h15_x1 ot_h15_y1
  set ot_h15_k [odb::dbBlockage_create $ot_h15_b [expr {round($ot_h15_x0 * $ot_h15_d)}] [expr {round($ot_h15_y0 * $ot_h15_d)}] \
              [expr {min(round($ot_h15_x1 * $ot_h15_d), [$ot_h15_die xMax])}] [expr {min(round($ot_h15_y1 * $ot_h15_d), [$ot_h15_die yMax])}]]
  $ot_h15_k setMaxDensity 15.0
  puts "OT_H15_HOME partial blockage $ot_h15_n {$ot_h15_r} max_density [$ot_h15_k getMaxDensity]"
}
unset ot_h15_b ot_h15_d ot_h15_die ot_h15_n ot_h15_r ot_h15_k ot_h15_x0 ot_h15_y0 ot_h15_x1 ot_h15_y1
