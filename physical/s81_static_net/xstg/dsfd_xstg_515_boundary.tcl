# S-NET xstg: both IO references follow their actual routed boundary clocks.
# The old name vw was not an insertion-reference clock in io_ref_routed.sdc;
# leaving it at zero caused ten or eleven extra input hold buffers per bit.
# Preserve the same clock relationships, 0.2T IO budgets and uncertainty.
set ::ot_ref_pre_cts 0
set_propagated_clock [get_clocks {core_clk wclk}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock ot_lb_v_wclk [get_ports {i*}]
set_input_delay -min 0 -clock ot_lb_v_wclk [get_ports {i*}]
set_output_delay 316.667 -clock vclk [get_ports {o*}]
set_output_delay -min 0 -clock vclk [get_ports {o*}]
source /src/physical/common_flow/io_ref_routed.sdc
