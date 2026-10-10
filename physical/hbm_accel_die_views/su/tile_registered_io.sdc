# Tile links launch from neighbouring registered boundaries on matched roots.
# Both launch phases are checked: chain heads may launch on rising edges, and
# lockup tile neighbours on falling edges. Half-cycle setup is therefore real.
set ti_c [get_clocks core_clk]
set ti_p [get_property $ti_c period]
create_clock -name peer_clk -period $ti_p -waveform [list 0 [expr {$ti_p/2}]]
set ti_lat 0
if {[info exists ::env(CK_TT_MEAN)]} {set ti_lat $::env(CK_TT_MEAN)}
if {[llength [get_libs -quiet *_FF_*]] && [info exists ::env(CK_FF_MEAN)]} {set ti_lat $::env(CK_FF_MEAN)}
set_clock_latency -source $ti_lat [get_clocks peer_clk]
set_clock_uncertainty -setup 60 [get_clocks peer_clk]
set_clock_uncertainty -hold 25 [get_clocks peer_clk]
set ti_in [delete_from_list [all_inputs] [get_ports clk]]
set_input_delay -max 166.6 -clock peer_clk $ti_in
set_input_delay -min 25 -clock peer_clk $ti_in
set_input_delay -max 166.6 -clock peer_clk -clock_fall -add_delay $ti_in
set_input_delay -min 25 -clock peer_clk -clock_fall -add_delay $ti_in
set_output_delay -max 166.6 -clock peer_clk [all_outputs]
set_output_delay -min -25 -clock peer_clk [all_outputs]
