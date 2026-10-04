# --step-tcl PRE_CTS hook for forwarded-clock link fixtures (ot_fwd_link_hop2): skip ORFS's repair_clock_inverters.
# That step clones every clock inverter next to its register loads, which merges a forwarded (inverted) clock into the
# launching stage's tree, i.e. builds one balanced synchronous tree across the link span.  A forwarded clock is the
# opposite: the forwarding inverter (ot_fwd_clk_inv) stays one cell at the launching end and TritonCTS builds the
# receiving stage's subtree from it, so the clock reaches the far end over the span beside its data bus.
if {[llength [info commands repair_clock_inverters]]} {
  rename repair_clock_inverters ot_orig_repair_clock_inverters
  proc repair_clock_inverters {args} { puts "OT_FWD: repair_clock_inverters skipped (forwarded-clock subtree kept)" }
}
# TritonCTS also balances the launching tree's latency against the forwarded subtree ("Balancing latency for clock
# incoming: inserted N delay buffers"), which would delay the launch by the whole span and undo the forwarding.  The
# receiving stage's latency is deliberately unbalanced here, so delay-buffer insertion is off for this fixture.
if {[llength [info commands clock_tree_synthesis]] && ![llength [info commands ot_orig_clock_tree_synthesis]]} {
  rename clock_tree_synthesis ot_orig_clock_tree_synthesis
  proc clock_tree_synthesis {args} {
    puts "OT_FWD: clock_tree_synthesis $args -delay_buffer_derate 0"
    uplevel 1 [list ot_orig_clock_tree_synthesis {*}$args -delay_buffer_derate 0]
  }
}
