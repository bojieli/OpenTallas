# S-NET dsfd_xstg_515 POST_CTS boundary: each virtual IO clock at its own tree's measured WC insertion midpoint
# (vclk <- core_clk, vw <- wclk), as physical/s81_die_views/hend/negcap/*_boundary.tcl.
set ::ot_ref_pre_cts 0
set_propagated_clock [get_clocks {core_clk wclk}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
proc ot_ins {clk scene} {
  sta::redirect_string_begin
  set rc [catch {report_clock_latency -clock $clk -scenes $scene}]
  set s [sta::redirect_string_end]
  if {!$rc && [regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} { return [list $lo $hi] }
  sta::redirect_string_begin
  catch {report_clock_latency -clock $clk}
  set s [sta::redirect_string_end]
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} { return [list $lo $hi] }
  return {}
}
foreach {c v} [list core_clk vclk wclk vw] {
  set wc [ot_ins $c WC]
  if {[llength $wc] == 0} { puts "post_cts_xstg: no $c latency"; continue }
  set L [expr {round(([lindex $wc 0] + [lindex $wc 1]) / 2.0)}]
  set_clock_latency $L [get_clocks $v]
  puts "post_cts_xstg: $c WC $wc -> $v latency $L"
}
set_input_delay 166.667 -clock vw [get_ports {i*}]
set_input_delay -min 0 -clock vw [get_ports {i*}]
set_output_delay 316.667 -clock vclk [get_ports {o*}]
set_output_delay -min 0 -clock vclk [get_ports {o*}]
