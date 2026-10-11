# nbr_in_ref_cts_hook.tcl ([cg] 2026-10-10): after clock_tree_synthesis, re-reference nbr_clk_i to the built tree's input
# pin-flop insertion (nbr_in_ref.tcl) before any CTS-stage repair; the written 4_cts.sdc carries the measured values.
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_nir_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_nir_cts_orig
  proc clock_tree_synthesis {args} {
    ot_nir_cts_orig {*}$args
    estimate_parasitics -placement
    set_propagated_clock [all_clocks]
    source /src/physical/common_flow/nbr_in_ref.tcl
    ot_nir_apply cts
  }
}
