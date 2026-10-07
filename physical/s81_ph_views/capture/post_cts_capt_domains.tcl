# Capture successor: preserve stream/serial output clock ownership after the
# common insertion hook. The legacy hook assigns core-clock minimum delay to
# every non-HBM output; t_vm/t_st belong to ser_clk and must use its WC/BC tree.
source /src/physical/s81_ph_views/tiles/pre_cts_ser_balance.tcl
ot_ser_balance
detailed_placement
estimate_parasitics -placement
source /src/physical/s81_ph_views/common/vclk_latency.tcl
ot_vclk_from_insertion 1
set ot_serial_outputs {}
foreach ot_p [all_outputs] {
  if {[regexp {^(t_vm|t_st)(\[|$)} [get_full_name $ot_p]]} {
    lappend ot_serial_outputs $ot_p
  }
}
if {[llength $ot_serial_outputs] == 0} { error "capture domain hook: no serial outputs" }
set ot_serial_wc [ot_clk_ins WC ser_clk]
set ot_serial_bc [ot_clk_ins BC ser_clk]
if {[llength $ot_serial_wc] != 2 || [llength $ot_serial_bc] != 2} {
  error "capture domain hook: WC and BC serial insertion required"
}
set ot_serial_L [expr {round(([lindex $ot_serial_wc 0] + [lindex $ot_serial_wc 1]) / 2.0)}]
set ot_serial_min [expr {$ot_serial_L - round([lindex $ot_serial_bc 0]) - 40}]
# Same +65 ps receiver hold obligation used by the core-domain budget: minimum
# insertion +40 ps output term +25 ps uncertainty. No hold uncertainty relaxed.
unset_output_delay -clock vclk $ot_serial_outputs
set_clock_latency $ot_serial_L [get_clocks vclk_s]
# Restate the original ser_clock_capt.sdc setup budget explicitly. This makes
# both bounds independent of any earlier output-delay overwrite by another hook.
set ot_serial_period [get_property [get_clocks ser_clk] period]
set ot_serial_max [expr {$ot_serial_period * 0.2 + 150}]
set_output_delay -max $ot_serial_max -clock vclk_s $ot_serial_outputs
set_output_delay -min $ot_serial_min -clock vclk_s $ot_serial_outputs
puts "OT_CAPTURE_DOMAINS serial_outputs=[llength $ot_serial_outputs] WC=$ot_serial_wc BC=$ot_serial_bc L=$ot_serial_L max=$ot_serial_max min=$ot_serial_min"
