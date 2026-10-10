# PRE_CTS hook (drive-1443, 2026-10-08): half-rate gclk of ot_ha2_tu_owner_banked_half.
# Root cause of ha2_h2_fixedpins_ca0d6a5a2-tt (SS -852.8 / FF -540.3): the hand-built gater u_icg (negedge flop en_l +
# AND2) sits at a LEAF of the ~1.0 ns clk tree and drives its own ~0.7 ns gclk tree, so every gclk sink is ~0.95 ns
# later than the clk sinks it talks to (gclk->clk setup -852, clk->gclk hold -540).  This plain-ORFS config never got
# the closure loop's OT_CTS_FIX_HOOKS (they only reach run_abi3_physical), so the fleet's fix was never applied here.
# Fix: physical/common_flow/cg_pushdown.tcl clones the AND (+ its en_l flop) per sink cluster (OT_CG_K sinks), placed at
# the cluster, so each clone's clock pin is a leaf of the clk tree and its gated subtree is one shallow level.  The
# generated clock gclk is then re-created on EVERY clone output (the SDC defined it on the single original pin; clones
# would otherwise propagate the full-rate clk), and clk propagation is stopped at the en_l outputs (the gclk edge comes
# from the AND's clock input; en_l only changes while clk is low).
source /src/physical/common_flow/cg_pushdown.tcl
proc ot_ha2_gclk_redefine {} {
  set pins {}
  foreach p [get_pins -hierarchical *] {
    set n [get_full_name $p]
    if {[regexp {u_icg.*/Y$} $n]} {
      set c [get_cells -of_objects $p]
      if {[regexp {AND} [get_property $c ref_name]]} { lappend pins $p }
    }
  }
  if {![llength $pins]} { error "OT_HA2_GCLK: no ICG AND output" }
  catch {delete_generated_clock [get_clocks gclk]}
  create_generated_clock -name gclk -source [get_ports clk] -divide_by 2 $pins
  set_clock_uncertainty -setup 60 [get_clocks gclk]
  set_clock_uncertainty -hold 25 [get_clocks gclk]
  set q {}
  foreach p [get_pins -hierarchical *] {
    if {[regexp {u_icg.*en_l.*/QN?$} [get_full_name $p]]} { lappend q $p }
  }
  if {[llength $q] && [catch {set_sense -type clock -stop_propagation -clocks [get_clocks clk] $q} e]} { puts "OT_HA2_GCLK: set_sense failed: $e" }
  puts "OT_HA2_GCLK: gclk on [llength $pins] gate output(s); clk stopped at [llength $q] en_l output(s)"
}
proc clock_tree_synthesis {args} {
  ot_cg_pushdown
  if {$::ot_cg_clones > 0} { estimate_parasitics -placement; repair_design }
  ot_ha2_gclk_redefine
  ot_cgpd_cts_orig {*}$args
}
