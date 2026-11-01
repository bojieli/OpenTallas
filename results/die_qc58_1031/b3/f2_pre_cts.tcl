# DIE-QC-58A NK form (2) PRE_CTS hook: the kit fc_dt lift (unchanged) + the post-CTS hop-ICG re-tap (f2_form2.tcl) + DPL fallback
source /work/fc_dt_lift_cts.tcl
source /work/f2_form2.tcl
if {[info commands ot_b3_dpl_inner] eq "" && [info commands detailed_placement] ne ""} {
  rename detailed_placement ot_b3_dpl_inner
  proc detailed_placement {args} {
    set r [ot_b3_dpl_inner {*}$args]
    if {[lsearch $args -incremental] < 0 && [catch {check_placement} m]} {
      puts "OT_B3_DPL: default legalizer left an illegal placement ($m) -> detailed_placement -use_diamond_legalizer"
      set r [ot_b3_dpl_inner {*}$args -use_diamond_legalizer]
    }
    return $r
  }
}
