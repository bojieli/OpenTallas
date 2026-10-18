# qfd_tt_head_static_h15 (Q-TTH15 2026-10-17): keep the controller in the E "home" band (E band x >= 216.6 + SE S band
# x >= 129.6, y <= 43.2) next to the mirrored macros' read/clk edge.  15% PARTIAL placement blockages on the N band
# (above the macro stack, x < 216.6) and the SW S band (x < 129.6, y < 43.2): repeaters on the ~575 W<->E crossing bits
# still fit, the controller logic cannot smear around the stack (h14d: 17.5% density ring).  Sourced from pre_gpl.tcl
# (pin_hook_before_flops) so global placement sees them; post_resize_relocate skips partial blockages.
set ot_hb [ord::get_db_block]
set ot_hd [$ot_hb getDbUnitsPerMicron]
set ot_hdie [$ot_hb getDieArea]
foreach {ot_hn ot_hr} [list N {0 198.768 216.6 222.48} SW_S {0 0 129.6 43.2}] {
  lassign $ot_hr x0 y0 x1 y1
  set ot_k [odb::dbBlockage_create $ot_hb [expr {round($x0 * $ot_hd)}] [expr {round($y0 * $ot_hd)}] \
              [expr {min(round($x1 * $ot_hd), [$ot_hdie xMax])}] [expr {min(round($y1 * $ot_hd), [$ot_hdie yMax])}]]
  $ot_k setMaxDensity 15.0
  puts "OT_H15_HOME partial blockage $ot_hn {$ot_hr} max_density [$ot_k getMaxDensity]"
}
