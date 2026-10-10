# strip-protect 2026-10-09: TA15 collars (ot_hbm_clock_reset_collars_rs) reset constraints.  ASAP7 time unit: ps.
# Replaces isolated.sdc for the successor.  Differences, each from the r4 failure (6_finish.rpt: por_n "input port
# clocked by hbm" -> recovery at a flop clocked by link, 1.35 ps LCM edge separation, -179 ps):
#   1. The AON reset intents are launched by a VIRTUAL clock aon_v (they are asynchronous to every destination
#      clock), never by a destination clock.
#   2. The raw ASSERT edge (falling, active-low) is the only false path: assertion is clockless by design.
#   3. The raw DEASSERT reaches only the synchroniser flops (*sync_q*): a bounded-skew window (max 500 ps / min 0,
#      clock latency ignored) so both synchroniser stages see the release within one cycle.  Recovery/removal there
#      is checked against that window, not waived.
#   4. Everything after the synchroniser is synchronous and timed with no exception: sync_q -> tree RESETN
#      recovery/removal in the destination clock, reg-to-reg, and the registered outputs against output delays.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
delete_clock [all_clocks]
create_clock -name stream -period 833.333333 [get_ports clk_stream]
create_clock -name serial -period 1111.111111 [get_ports clk_serial]
create_clock -name hbm -period 1024 [get_ports clk_hbm]
create_clock -name link -period 833.333333 [get_ports clk_link]
create_clock -name aon_v -period 3000
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ot_async [get_ports {por_n pll_reset_n pll_lock phy_reset_intent_n* link_reset_intent_n* coll_reset_intent_n cmd_reset_intent_n}]
set_input_delay -min 25 -clock aon_v $ot_async
set_input_delay -max 100 -clock aon_v $ot_async
set_output_delay -min 25 -clock hbm [get_ports phy_reset_n*]
set_output_delay -max 100 -clock hbm [get_ports phy_reset_n*]
set_output_delay -min 25 -clock link [get_ports link_reset_n*]
set_output_delay -max 100 -clock link [get_ports link_reset_n*]
set_output_delay -min 25 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -max 100 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -min 25 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set_output_delay -max 100 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set ot_sync [get_cells -hierarchical -quiet *sync_q*]
puts "OT_TA15_RS: [llength $ot_sync] synchroniser cells"
set_false_path -fall_from $ot_async
if {[llength $ot_sync]} {
  set_max_delay 500 -ignore_clock_latency -rise_from $ot_async -to $ot_sync
  set_min_delay 0 -ignore_clock_latency -rise_from $ot_async -to $ot_sync
}
