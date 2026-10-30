# DIE-KV-38 KV-022 declared CDC (COORD 18:21 ruling: existing declared-CDC form). Form = rtl ot_fdi_phy_cdc.sv header
# "SDC intent" (clk <-> clk_phy asynchronous; only arcs inside u_rx/u_tx ot_async_fifo + tx_up/reset synchronisers),
# same as physical/ref_tile/dsfd_vm_fcn_m5/clock.sdc proc ot_fh_cdc: Gray/online -> first sync flop max 0.5 T, no hold;
# FIFO storage -> read-domain register max T-60, no hold; tx_up level / PHY reset async input -> first stage false path.
set ot_cdc_T 833.0
set ot_cdc_sync {}; set ot_cdc_lvl {}; set ot_cdc_mrx {}; set ot_cdc_mtx {}; set ot_cdc_rst {}
foreach c [all_registers -cells] {
  set n [get_full_name $c]
  if {[regexp {u_fdi_cdc[.]u_(rx|tx)[.](wr_gray_r1|rd_gray_w1)\[[0-9]+\]} $n] || [regexp {u_fdi_cdc[.]u_(rx|tx)[.](wr_online_r1|rd_online_w1)([^0-9a-z_]|$)} $n]} {
    lappend ot_cdc_sync $c
  } elseif {[regexp {u_fdi_cdc[.]up_s\[0\]} $n]} { lappend ot_cdc_lvl $c
  } elseif {[regexp {u_fdi_cdc[.]u_rx[.]mem\[} $n]} { lappend ot_cdc_mrx $c
  } elseif {[regexp {u_fdi_cdc[.]u_tx[.]mem\[} $n]} { lappend ot_cdc_mtx $c
  } elseif {[regexp {u_fdi_cdc[.]u_prs[.]reset_pipe\[} $n]} {
    foreach p [get_pins -of_objects $c] { if {[get_property $p lib_pin_name] eq "RESETN"} { lappend ot_cdc_rst $p } }
  }
}
puts "OT_CDC_FDI sync [llength $ot_cdc_sync] lvl [llength $ot_cdc_lvl] mem_rx [llength $ot_cdc_mrx] mem_tx [llength $ot_cdc_mtx] prs_rst [llength $ot_cdc_rst]"
if {[llength $ot_cdc_sync]} { set_max_delay -ignore_clock_latency [expr {0.5 * $ot_cdc_T}] -to $ot_cdc_sync; set_false_path -hold -to $ot_cdc_sync }
if {[llength $ot_cdc_lvl]} { set_false_path -to $ot_cdc_lvl }
if {[llength $ot_cdc_rst]} { set_false_path -to $ot_cdc_rst }
if {[llength $ot_cdc_mrx]} { set_max_delay -ignore_clock_latency [expr {$ot_cdc_T - 60.0}] -from $ot_cdc_mrx -to [get_clocks clk]; set_false_path -hold -from $ot_cdc_mrx -to [get_clocks clk] }
if {[llength $ot_cdc_mtx]} { set_max_delay -ignore_clock_latency [expr {$ot_cdc_T - 60.0}] -from $ot_cdc_mtx -to [get_clocks clk_clk_phy]; set_false_path -hold -from $ot_cdc_mtx -to [get_clocks clk_clk_phy] }
