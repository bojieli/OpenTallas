# Intrinsic source0 child interface. Native source/driver/pin binding is separate.
# Fixed 833.333ps, positive edge, original source slew preserved. Each loaded
# corner measures its own real boundary-register mean; no scalar/median target.
create_clock -name core_clk -period 833.333 [get_ports ck]
create_clock -name vclk -period 833.333
set_clock_latency -source 0 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
foreach clock [all_clocks] {
    unset_input_delay -clock $clock [all_inputs]
    unset_input_delay -clock $clock -clock_fall [all_inputs]
    unset_output_delay -clock $clock [all_outputs]
    unset_output_delay -clock $clock -clock_fall [all_outputs]
}
set_input_delay 256.667 -max -clock vclk [all_inputs -no_clocks]
set_input_delay 0 -min -clock vclk [all_inputs -no_clocks]
set_output_delay 256.667 -max -clock vclk [all_outputs]
# Sender75 + hold uncertainty25 = H100; receiver min0 preserves H1 split.
set_output_delay -75 -min -clock vclk [all_outputs]
source /src/physical/common_flow/io_ref_routed.sdc
if {![dict exists $ot_ir_ins core_clk]} { error "ENGC child boundary mean unavailable" }
lassign [dict get $ot_ir_ins core_clk] R lo hi n kind
puts "ENGC_CHILD_MEAN core_clk R=$R lo=$lo hi=$hi n=$n kind=$kind; source0 fixed833.333 H100"
