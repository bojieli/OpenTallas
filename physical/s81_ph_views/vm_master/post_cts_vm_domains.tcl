# s81-vm-1011: post-CTS: core_clk IO at the measured insertion (common vclk hook), then the stream-domain IO against
# vclk_t at the measured str_clk insertion (as post_cts_capt_domains.tcl for the capture's serial outputs).
source /src/physical/s81_ph_views/common/vclk_latency.tcl
ot_vclk_from_insertion 1
if {[llength [get_clocks -quiet str_clk]]} {
  set ot_t_wc [ot_clk_ins WC str_clk]
  set ot_t_bc [ot_clk_ins BC str_clk]
  if {[llength $ot_t_wc] == 2 && [llength $ot_t_bc] == 2} {
    set ot_t_L [expr {round(([lindex $ot_t_wc 0] + [lindex $ot_t_wc 1]) / 2.0)}]
    set_clock_latency $ot_t_L [get_clocks vclk_t]
    puts "OT_VM_DOMAINS str_clk insertion L=$ot_t_L WC=$ot_t_wc BC=$ot_t_bc"
  } else { puts "OT_VM_DOMAINS: no str_clk insertion report; vclk_t latency unchanged" }
}
