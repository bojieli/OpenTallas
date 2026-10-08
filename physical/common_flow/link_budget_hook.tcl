# CLAUDE setup-triage 2026-10-07: route-time adoption of the consistent die-link budget.  ORFS PRE_CTS hook (chain it via
# OT_CTS_FIX_HOOKS): after clock_tree_synthesis builds the tree, source link_budget_consistent.sdc (virtual clock at the
# measured mid insertion, -max -add_delay), so CTS-stage and GRT repair optimise against the split the sign-off checks;
# ORFS write_sdc carries it into 4_cts.sdc .. 6_final.sdc.  Knobs: env ot_lb_skew / ot_lb_link / ot_lb_sfrac.
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_lbh_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_lbh_cts_orig
  proc clock_tree_synthesis {args} {
    ot_lbh_cts_orig {*}$args
    estimate_parasitics -placement
    set_propagated_clock [all_clocks]
    foreach d [list [file dirname [info script]] /work/hooks /src/physical/common_flow] {
      if {[file exists $d/link_budget_consistent.sdc]} { read_sdc $d/link_budget_consistent.sdc; return }
    }
    error "OT_LINK_BUDGET hook: link_budget_consistent.sdc not found"
  }
}
