# tap_fclat_cts_hook.tcl (hbm-phys vm8 2026-10-10): OT_CTS_FIX_HOOKS member (list it LAST).  After clock_tree_synthesis builds
# the half's tap trees, the per-tap source latency is re-derived from THIS route's tree (tap_fclat.tcl, scene of mode ss)
# before any CTS-stage timing repair, so the repair and the written 4_cts.sdc .. 6_final.sdc see the taps balanced the
# way the die balances them.  The FF scene re-derives its own when ot_mm_sync reads fclat.sdc (route_ff_sdc).
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_fcl_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_fcl_cts_orig
  proc clock_tree_synthesis {args} {
    ot_fcl_cts_orig {*}$args
    estimate_parasitics -placement
    set_propagated_clock [all_clocks]
    source /src/physical/hbm_accel_die_views/vm/vcut8/tap_fclat.tcl
    ot_fcl_apply cts
  }
}
