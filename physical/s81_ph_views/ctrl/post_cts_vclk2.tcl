# POST_CTS (dsfd_ctrl): vclk at the measured core_clk (cks) insertion and vclk_h at the measured hbm_clk (ckh) insertion
source /src/physical/s81_ph_views/common/vclk_latency.tcl
ot_vclk_from_insertion 1
sta::redirect_string_begin
report_clock_latency -clock hbm_clk
set ot_s [sta::redirect_string_end]
if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> lo hi]} {
  set L [expr {round(($lo + $hi) / 2.0)}]
  set_clock_latency $L [get_clocks vclk_h]
  puts "ot_vclk_h: hbm_clk insertion $lo .. $hi ps -> vclk_h latency $L ps"
}
