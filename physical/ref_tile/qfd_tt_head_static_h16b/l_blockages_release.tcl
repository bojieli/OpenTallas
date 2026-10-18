# qfd_tt_head_static_h16: remove the 0.5% W/N channel blockages (l_blockages.tcl) before detailed placement (DPL counts
# fixed taps / endcaps under a placement blockage as not placed in rows: h15 gate 1 DPL-0004 -> DPL-0033).
set ot_h16b_b [ord::get_db_block]
set ot_h16b_n 0
foreach ot_h16b_k [$ot_h16b_b getBlockages] {
  if {![$ot_h16b_k isSoft] && abs([$ot_h16b_k getMaxDensity] - 0.5) < 1e-3} {
    if {[catch {odb::dbBlockage_destroy $ot_h16b_k}]} { $ot_h16b_k setSoft; $ot_h16b_k setMaxDensity 0.0 }
    incr ot_h16b_n
  }
}
puts "OT_H16B_L released $ot_h16b_n channel blockages before DPL"
unset ot_h16b_b ot_h16b_n ot_h16b_k
