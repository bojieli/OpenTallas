# --step-tcl PRE_CTS hook for forwarded-clock link fixtures (ot_fwd_link_hop2): skip ORFS's repair_clock_inverters.
# That step clones every clock inverter next to its register loads, which merges a forwarded (inverted) clock into the
# launching stage's tree, i.e. builds one balanced synchronous tree across the link span.  A forwarded clock is the
# opposite: the forwarding inverter (ot_fwd_clk_inv) stays one cell at the launching end and TritonCTS builds the
# receiving stage's subtree from it, so the clock reaches the far end over the span beside its data bus.
if {[llength [info commands repair_clock_inverters]]} {
  rename repair_clock_inverters ot_orig_repair_clock_inverters
  proc repair_clock_inverters {args} { puts "OT_FWD: repair_clock_inverters skipped (forwarded-clock subtree kept)" }
}
# (TritonCTS's per-clock latency balancing would also pad the launching tree to the forwarded subtree's latency;
# fwd_hop2.sdc defines the forwarded clock as its own generated clock at the forwarding inverter, so it is a separate
# clock root and nothing is balanced across the span.)
