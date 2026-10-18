# qfd_tt_head_static_h16 (Q-TTH16 2026-10-17): the abutted MY SRAM stack sits in the NW corner (x 22.464, y 43.2..198.8)
# with its read/clk edge facing E.  The 20-um W and N macro-edge channels (production rule) carry only the 146 far-edge
# write nets (w_mask / wd_in[511:266] after MY); they get a near-hard (0.5%) placement blockage for GLOBAL placement so
# the std cells form ONE contiguous L (E band x >= 199.2 + S band y <= 37.8) beside the read edge, not a ring around
# the stack (h15a).  Released before DPL (home_blockages_release-style) so fixed taps / endcaps under them stay legal.
set ot_h16_b [ord::get_db_block]
set ot_h16_d [$ot_h16_b getDbUnitsPerMicron]
set ot_h16_die [$ot_h16_b getDieArea]
foreach {ot_h16_n ot_h16_r} [list W {0 37.8 22.464 222.48} N {22.464 198.768 199.152 222.48}] {
  lassign $ot_h16_r ot_h16_x0 ot_h16_y0 ot_h16_x1 ot_h16_y1
  set ot_h16_k [odb::dbBlockage_create $ot_h16_b [expr {round($ot_h16_x0 * $ot_h16_d)}] [expr {round($ot_h16_y0 * $ot_h16_d)}] \
              [expr {min(round($ot_h16_x1 * $ot_h16_d), [$ot_h16_die xMax])}] [expr {min(round($ot_h16_y1 * $ot_h16_d), [$ot_h16_die yMax])}]]
  $ot_h16_k setMaxDensity 0.5
  puts "OT_H16_L blockage $ot_h16_n {$ot_h16_r} max_density [$ot_h16_k getMaxDensity]"
}
unset ot_h16_b ot_h16_d ot_h16_die ot_h16_n ot_h16_r ot_h16_k ot_h16_x0 ot_h16_y0 ot_h16_x1 ot_h16_y1
