# SERDES-H-FORM reset cohorts (S81-SERDES-GEN 11-17), sourced by pre_cts.tcl right before clock_taps.tcl.
# Computes the bounded reset-relay cohorts from the CURRENT placed block (relay + collector positions, the plan's tap ports as the
# light roots) with reset_cohort_model.py, then sets OT_SERDES_RESET_COHORT / OT_SERDES_RELAY_COHORTS / OT_TAP_GROUP_FIXED for
# clock_taps.tcl.  No hand file, no t13 data.  A block without compiled reset relays (no u_rrl_N) is left alone; any other model
# failure stops the kit (fail closed).  Gen env OT_SERDES_COHORTS=0 in the kit config turns it off.
if {[info exists ::env(OT_SERDES_COHORTS)] && $::env(OT_SERDES_COHORTS) eq "0"} {
  puts "OT_SERDES_COHORTS off"
} else {
  source /work/serdes_reset_graph.tcl
  set ot_sc_dir $::env(RESULTS_DIR)
  ot_serdes_reset_graph $ot_sc_dir/serdes_reset_graph.tsv
  set ot_sc_f [open $ot_sc_dir/serdes_reset_graph.tsv];set ot_sc_t [read $ot_sc_f];close $ot_sc_f
  if {![regexp {\nNODE\tRRL\t} $ot_sc_t]} {
    puts "OT_SERDES_COHORTS none: no compiled reset relays in this block"
  } else {
    exec python3 /work/reset_cohort_model.py $ot_sc_dir/serdes_reset_graph.tsv $ot_sc_dir/serdes_reset_cohorts.json --type $::env(DESIGN_NICKNAME) --source "generated serdes_cohorts.tcl at PRE_CTS" >@stdout 2>@stderr
    set ot_sc_old [expr {[info exists ::env(OT_TAP_GROUP_FIXED)] ? $::env(OT_TAP_GROUP_FIXED) : ""}]
    exec python3 /work/serdes_cohorts_env.py $ot_sc_dir/serdes_reset_cohorts.json $ot_sc_dir/serdes_cohorts_env.tcl $ot_sc_old >@stdout 2>@stderr
    source $ot_sc_dir/serdes_cohorts_env.tcl
    # A native relay-only partition legitimately has no local collector. Derive the
    # expected ids from the sealed bound wrapper, independently of the compiled ODB.
    unset -nocomplain ::env(OT_SERDES_EXPECTED_LOCAL_COLLECTORS)
    if {[info exists ::env(DESIGN_NAME)]} {
      set ot_sc_bound [file join /work rtl "$::env(DESIGN_NAME)_bound.sv"]
      if {[file readable $ot_sc_bound]} {
        set ot_sc_f [open $ot_sc_bound]
        set ot_sc_rtl [read $ot_sc_f]
        close $ot_sc_f
        set ot_sc_ids {}
        foreach {decl id} [regexp -all -inline {\mot_dp_landing_collect\M[^;]*?\mu_cland_collect_rst_rl_([0-9]+)\M\s*\(} $ot_sc_rtl] {
          lappend ot_sc_ids $id
        }
        set ::env(OT_SERDES_EXPECTED_LOCAL_COLLECTORS) [lsort -integer -unique $ot_sc_ids]
      }
    }
  }
}
