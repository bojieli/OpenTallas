# DPL multi-pass legalization (S-QA0 2026-10-18), sourced from a kit's PRE_CTS hook.
# ORFS cts.tcl legalizes the post-CTS hold buffers in ONE detailed_placement call and then runs check_placement.
# On the A0 ROM-leaf parents (qfd_tile_n{k,l}_romleaf_c1, c1r8 kits, ENABLE_DPO=0 because improve_placement crashes
# with 'bad optional access') the NegotiationLegalizer leaves a few cells stuck after ~26k hold buffers
# (NK 12 / NL 100 cells, DPL-0701 -> check_placement DPL-0033).  A further pass from the near-legal state converges
# (c1r7 NK cts.log: the pass after improve_placement 'converged at iteration 8').  Every detailed_placement call in
# the stage therefore runs up to three passes; a pass on an already-legal design is a no-op legalization.  No check is
# suppressed: ORFS' own check_placement still runs after the last pass and still fails the stage on any violation.
if {[llength [info commands ::ot_dplmp_orig]] == 0} {
  rename detailed_placement ::ot_dplmp_orig
  proc detailed_placement {args} {
    for {set k 1} {$k <= 3} {incr k} {
      puts "OT_DPL_MULTIPASS: detailed_placement pass $k"
      ::ot_dplmp_orig {*}$args
    }
  }
}
