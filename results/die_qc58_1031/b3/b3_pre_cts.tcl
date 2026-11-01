# DIE-QC-58A B3 PRE_CTS hook: the kit fc_dt lift (unchanged) + the B3 post-CTS early-branch wrapper (b3_early.tcl)
source /work/fc_dt_lift_cts.tcl
source /work/b3_early.tcl
# DIE-QC-58A: legalization fallback (kit-local). The NegotiationLegalizer left 4 overlapping tx flops after ~19k FF hold
# buffers (DPL-0033 at check_placement). When the default detailed_placement leaves an illegal placement, rerun it with
# the diamond legalizer; check_placement in cts.tcl still decides.
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
