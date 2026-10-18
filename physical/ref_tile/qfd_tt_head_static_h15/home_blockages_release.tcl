# qfd_tt_head_static_h15: remove the 15% home partial blockages (home_blockages.tcl) before detailed placement.  They only
# steer global placement; DPL check_placement counts the fixed tap / endcap cells under any placement blockage as "not
# placed in rows" (h15 gate 1: DPL-0004 x 925 -> DPL-0033).
set ot_h15_b [ord::get_db_block]
set ot_h15_n 0
foreach ot_h15_k [$ot_h15_b getBlockages] {
  if {![$ot_h15_k isSoft] && abs([$ot_h15_k getMaxDensity] - 15.0) < 1e-3} {
    if {[catch {odb::dbBlockage_destroy $ot_h15_k}]} { $ot_h15_k setSoft; $ot_h15_k setMaxDensity 0.0 }
    incr ot_h15_n
  }
}
puts "OT_H15_HOME released $ot_h15_n partial blockages before DPL"
unset ot_h15_b ot_h15_n ot_h15_k
