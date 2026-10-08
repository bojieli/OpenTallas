# CLAUDE S81-PH capture tiles (dsfd_capt_grp t_vm, dsfd_capt_ctl t_st): as ../common/ser_clock_capture.sdc. Second (serial 0.9 GHz) clock of a two-domain S81 view on port ckv, related 3:4 to core_clk
# (one die PLL, /4 vs /3 of 3.6 GHz: ot_ratio_cdc_fifo timing contract, every crossing arc flop -> flop and timed at
# the 278 ps edge window).  Same margin-first budgets as io_vclk_m_770.sdc: setup uncertainty 123 ps (route),
# 60 ps at sign-off (signoff_unc60.sdc applies to all clocks); serial-domain outputs (t_*) budgeted 0.2 T + 150 ps
# against vclk_s at the measured ser_clk insertion (post_cts_vclk2.tcl).  Resets are asynchronous assert,
# synchronised release inside the view: no timing from the rst/rsv pins.
create_clock -name ser_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {ckv}]
catch {unset_input_delay -clock vclk [get_ports {ckv}]}
create_clock -name vclk_s -period [get_property [get_clocks ser_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {ser_clk vclk_s}]
set_clock_uncertainty -hold 25 [get_clocks {ser_clk vclk_s}]
set_clock_latency 770 [get_clocks {ser_clk vclk_s}]
set ot_so [get_ports -quiet {t_vm[*] t_st[*]}]
if {[llength $ot_so]} { unset_output_delay -clock vclk $ot_so
set_output_delay [expr {[get_property [get_clocks ser_clk] period] * 0.2 + 150}] -clock vclk_s $ot_so
set_output_delay -min 0 -clock vclk_s $ot_so }
set ot_si [get_ports -quiet {nothing_here}]
if {[llength $ot_si]} {
  unset_input_delay -clock vclk $ot_si
  set_input_delay [expr {[get_property [get_clocks ser_clk] period] * 0.2 + 150}] -clock vclk_s $ot_si
  set_input_delay -min 0 -clock vclk_s $ot_si
}
set_false_path -from [get_ports {rst rsv}]
