# CLAUDE S81-PH POST_CTS for two-domain views: vclk at core_clk's measured insertion (post_cts_vclk.tcl) and vclk_s at
# ser_clk's measured insertion.
source /src/physical/s81_ph_views/common/vclk_latency.tcl
ot_vclk_from_insertion 1
sta::redirect_string_begin
report_clock_latency -clock ser_clk
set ot_s [sta::redirect_string_end]
if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> lo hi]} {
  set_clock_latency [expr {round(($lo + $hi) / 2.0)}] [get_clocks vclk_s]
  puts "post_cts_vclk2: ser_clk insertion $lo .. $hi ps -> vclk_s"
}
