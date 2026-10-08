# qfd_io_xfifo sign-off at 833.333 ps (all four clocks; propagated; 60 / 25 ps)
create_clock -name ck -period 833.333 [get_ports ck]
create_clock -name cku -period 833.333 [get_ports cku]
create_clock -name cks -period 833.333 [get_ports cks]
create_clock -name ckd -period 833.333 [get_ports ckd]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
# crossings: Gray pointer -> first synchroniser flop, and the read mux -> capture register: datapath budget of one
# period minus the setup uncertainty in both directions (no static phase relation); hold needs only a non-negative delay
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks cku]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks cku]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks cks]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks cks]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks ckd]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks ckd]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cku] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cku] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cku] -to [get_clocks cks]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cku] -to [get_clocks cks]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cku] -to [get_clocks ckd]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cku] -to [get_clocks ckd]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cks] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cks] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cks] -to [get_clocks cku]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cks] -to [get_clocks cku]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks cks] -to [get_clocks ckd]
set_min_delay -ignore_clock_latency 0 -from [get_clocks cks] -to [get_clocks ckd]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ckd] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ckd] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ckd] -to [get_clocks cku]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ckd] -to [get_clocks cku]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ckd] -to [get_clocks cks]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ckd] -to [get_clocks cks]
set ::env(OT_IO_SKEW_INTER) 150
set ::env(OT_IO_HOLD_SKEW) 50
# die-context boundary per clock domain (post-CTS): referenced to the propagated arrival L at a register of the
# block's tree in that domain; 0.2 T outside + OT_IO_SKEW_INTER (every xfifo port crosses a die wire to another clock
# region: 150 ps), hold allowance OT_IO_HOLD_SKEW (50).
set ot_sk [expr {[info exists ::env(OT_IO_SKEW_INTER)] ? $::env(OT_IO_SKEW_INTER) : 150}]
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk ins outs} {
  ck {i_ucie_tx_v i_ucie_tx[*] i_serdes_tx_v i_serdes_tx[*] o_ucie_rx_cr o_serdes_rx_cr o_seq_coll_cr} {i_ucie_tx_cr i_serdes_tx_cr o_ucie_rx_v o_ucie_rx[*] o_serdes_rx_v o_serdes_rx[*] o_seq_coll_v o_seq_coll[*] fault_ck}
  cku {o_ucie_tx_cr i_ucie_rx_v i_ucie_rx[*]} {o_ucie_tx_v o_ucie_tx[*] i_ucie_rx_cr fault_cku}
  cks {o_serdes_tx_cr i_serdes_rx_v i_serdes_rx[*]} {o_serdes_tx_v o_serdes_tx[*] i_serdes_rx_cr fault_cks}
  ckd {i_seq_coll_v i_seq_coll[*]} {i_seq_coll_cr fault_ckd}
} {
  set ref [lindex [all_registers -clock $clk -clock_pins] 0]
  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
  set T [get_property [get_clocks $clk] period]
  puts "QDM $clk ref [get_full_name $ref] L max $lmax min $lmin skew $ot_sk"
  set_input_delay  [expr {0.2*$T + $lmax + $ot_sk}] -max -clock $clk [get_ports $ins]
  set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]          -min -clock $clk [get_ports $ins]
  set_output_delay [expr {0.2*$T - $lmax + $ot_sk}] -max -clock $clk [get_ports $outs]
  set_output_delay [expr {-$lmin - $ot_hk}]         -min -clock $clk [get_ports $outs]
}
set_false_path -from [get_ports rst_n]
