# fe-push-ds-1010 2026-10-10 dsfd_wfc_crp (as ser_clock_vmx.sdc): the 0.9 GHz VM-side ports of the WFC credit-port tile on
# the second (serial) clock ckv, related 3:4 to core_clk.  The tile has NO ck <-> ckv crossing (its ck and ckv halves
# share no signal); both clocks are declared so every serial-domain port is budgeted against vclk_s, 0.2 T + 150 ps.
# Resets: asynchronous assert, synchronised release inside (ot_rst_relay per domain), so no timing from rst / rsv; the
# relay copies t_krst / t_krsv drive only the kit's asynchronous reset synchronisers (ot_dsrom_mtp_rstsync in every kit
# element), so they are not timed against a capture clock either.
create_clock -name ser_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {ckv}]
catch {unset_input_delay -clock vclk [get_ports {ckv}]}
create_clock -name vclk_s -period [get_property [get_clocks ser_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {ser_clk vclk_s}]
set_clock_uncertainty -hold 25 [get_clocks {ser_clk vclk_s}]
set_clock_latency 770 [get_clocks {ser_clk vclk_s}]
set ot_so [get_ports -quiet {t_swv[*] t_swd[*] t_srv[*] t_srd[*] t_kswr[*] t_kswa[*] t_ksrr[*]}]
if {[llength $ot_so]} { unset_output_delay -clock vclk $ot_so
set_output_delay [expr {[get_property [get_clocks ser_clk] period] * 0.2 + 150}] -clock vclk_s $ot_so
set_output_delay -min 0 -clock vclk_s $ot_so }
set ot_si [get_ports -quiet {f_swc[*] f_swa[*] f_src[*] f_kswv[*] f_kswd[*] f_ksrv[*] f_ksrd[*]}]
if {[llength $ot_si]} {
  unset_input_delay -clock vclk $ot_si
  set_input_delay [expr {[get_property [get_clocks ser_clk] period] * 0.2 + 150}] -clock vclk_s $ot_si
  set_input_delay -min 0 -clock vclk_s $ot_si
}
set_false_path -from [get_ports {rst rsv}]
set_false_path -to [get_ports {t_krst t_krsv}]
