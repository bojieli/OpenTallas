# CP pin-margin sign-off (read by corner STA after the routed design, SPEF and propagated clock):
# 833.333 ps, setup uncertainty 60 ps (AGENTS.md SS60/FF25), IO 0.2 T + 150 ps against vclk at THIS corner's measured
# mean core_clk insertion (rise), inputs/outputs -min 0. Accept: SS >= +40 ps, FF >= +15 ps on every endpoint.
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
sta::redirect_string_begin
report_clock_latency -clock core_clk
set ot_lat [sta::redirect_string_end]
if {![regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_lat -> ot_lo ot_hi]} {error "no core_clk insertion: $ot_lat"}
set ot_L [expr {($ot_lo + $ot_hi) / 2.0}]
set_clock_latency $ot_L [get_clocks vclk]
puts "OT_VCLK_INSERTION $ot_lo $ot_hi $ot_L"
set ot_in [all_inputs -no_clocks]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
