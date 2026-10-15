# el1011-ds-vm/be 2026-10-11: stream domain of the BE v3 slice tile dsfd_vm_be_sl (appended after the IO margin sdc).
# As str_clock_vm.sdc (str_clk = 3/4 of the serial period on cks; vclk_t at the stream insertion; vrv / vrq leave in the
# stream domain) plus the relayed synchronous stream reset rns_in (a stream-domain register in the parent).  No false paths:
# rn_in / rns_in are synchronous relay outputs and are timed.
create_clock -name str_clk -period [expr {[get_property [get_clocks core_clk] period] * 3.0 / 4.0}] [get_ports {cks}]
catch {unset_input_delay -clock vclk [get_ports {cks}]}
create_clock -name vclk_t -period [get_property [get_clocks str_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {str_clk vclk_t}]
set_clock_uncertainty -hold 25 [get_clocks {str_clk vclk_t}]
set_clock_latency 770 [get_clocks {str_clk vclk_t}]
set ot_to [get_ports {vrv* vrq*}]
unset_output_delay -clock vclk $ot_to
set_output_delay [expr {[get_property [get_clocks str_clk] period] * 0.2 + 150}] -clock vclk_t $ot_to
set_output_delay -min 0 -clock vclk_t $ot_to
set ot_ti [get_ports {rns_in}]
unset_input_delay -clock vclk $ot_ti
set_input_delay [expr {[get_property [get_clocks str_clk] period] * 0.2 + 150}] -clock vclk_t $ot_ti
set_input_delay -min 0 -clock vclk_t $ot_ti
