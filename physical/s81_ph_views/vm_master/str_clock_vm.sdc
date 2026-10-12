# s81-vm-1011: second clock of the VM master FE / BE views: cks = the stream 1.2 GHz clock (dsfd_sp_ctrl side: engine
# adapter, ctrl VM port ratio CDC), related 4:3 to core_clk = ck (serial 0.9 GHz; one die PLL, ot_ratio_cdc_fifo timing
# contract: every crossing arc flop -> flop, timed at the 278 ps edge window).  Margin-first budgets as io_vclk_m_770.sdc;
# stream-domain IO budgeted 0.2 T + 150 ps against vclk_t (latency set at the measured str_clk insertion post-CTS).
create_clock -name str_clk -period [expr {[get_property [get_clocks core_clk] period] * 3.0 / 4.0}] [get_ports {cks}]
catch {unset_input_delay -clock vclk [get_ports {cks}]}
create_clock -name vclk_t -period [get_property [get_clocks str_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {str_clk vclk_t}]
set_clock_uncertainty -hold 25 [get_clocks {str_clk vclk_t}]
set_clock_latency 770 [get_clocks {str_clk vclk_t}]
set ot_to [get_ports -quiet {dv* dt* vrv* vrq*}]
if {[llength $ot_to]} { unset_output_delay -clock vclk $ot_to
set_output_delay [expr {[get_property [get_clocks str_clk] period] * 0.2 + 150}] -clock vclk_t $ot_to
set_output_delay -min 0 -clock vclk_t $ot_to }
set ot_ti [get_ports -quiet {vwe* vwa* vwd* vre* vra* cv* cd*}]
if {[llength $ot_ti]} { unset_input_delay -clock vclk $ot_ti
set_input_delay [expr {[get_property [get_clocks str_clk] period] * 0.2 + 150}] -clock vclk_t $ot_ti
set_input_delay -min 0 -clock vclk_t $ot_ti }
set_false_path -from [get_ports {rst* rss*}]
# FE -> BE composition status / BE -> FE credit: sticky status and a credit pulse (no fixed-cycle requirement on fe_flt)
set_false_path -to [get_ports -quiet {fe_flt*}]
set_false_path -from [get_ports -quiet {fe_flt*}]
