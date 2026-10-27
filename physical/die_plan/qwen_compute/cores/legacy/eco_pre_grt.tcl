# FLOW-CLKFREEZE 2026-10-27 QC warm hold ECO PRE_GLOBAL_ROUTE hook (staged by mk_hold_qc.sh as /work/eco_pre_grt.tcl).
# The ECO starts do-5_1_grt from a COMPLETED route (4_cts.odb = 6_final.odb): every net already has a wire, so the
# ORFS global_route pass routes 0 nets and its own 'estimate_parasitics -global_routing' (before the POST hook) aborts
# with EST-0005 (vmr_f4k_final canary 11:53).  Only in that case (no GRT routes at all) the call reads the route's own
# RCX SPEF instead -- the parasitics of exactly this DB; any call with GRT routes runs unchanged.  Then the kit's own
# PRE_GLOBAL_ROUTE hook (OT_KIT_PRE_GRT, e.g. vclk bind) runs as before.
# Fillers carry no signal/clock ITerms; free their sites for the data ECO.
remove_fillers
if {[info commands ::ot_eco_est_orig] eq ""} {
  rename estimate_parasitics ::ot_eco_est_orig
  proc estimate_parasitics {args} {
    if {[lsearch -exact $args -global_routing] >= 0 && ![grt::have_routes]} {
      set s $::env(RESULTS_DIR)/6_final.spef
      if {![file exists $s]} { error "OT_ECO_EST: no GRT routes and no routed SPEF $s" }
      puts "OT_ECO_EST routed DB, no GRT routes: read_spef $s (instead of estimate_parasitics $args)"
      read_spef $s
      return
    }
    return [::ot_eco_est_orig {*}$args]
  }
}
if {[info exists ::env(OT_KIT_PRE_GRT)] && $::env(OT_KIT_PRE_GRT) ne ""} { source $::env(OT_KIT_PRE_GRT) }
