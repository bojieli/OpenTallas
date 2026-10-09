# Fused-head real-clock boundary references, retaining cl_route.sh's 250ps setup
# and sender-only 50ps hold windows. Opt-in: read after io_ref_routed.sdc.
# The original sign-off used calibration SS/FF insertion after the route tree changed;
# io_ref_routed only updates virtual clocks, not delays referencing real core_clk.
if {![info exists ::ot_ir_ins] || ![dict exists $::ot_ir_ins core_clk]} {
  error "fused-head boundary requires routed core_clk insertion from io_ref_routed.sdc"
}
lassign [dict get $::ot_ir_ins core_clk] L lo hi n kind
set_input_delay -max [expr {$L + 250.0}] -clock core_clk [all_inputs -no_clocks]
set_input_delay -min $L -clock core_clk [all_inputs -no_clocks]
set_output_delay -max [expr {250.0 - $L}] -clock core_clk [all_outputs]
set_output_delay -min [expr {-($L + 50.0)}] -clock core_clk [all_outputs]
puts "OT_FH_REAL_BOUNDARY core_clk L $L ($lo..$hi), retained setup 250 hold sender 50; $n $kind sinks"
