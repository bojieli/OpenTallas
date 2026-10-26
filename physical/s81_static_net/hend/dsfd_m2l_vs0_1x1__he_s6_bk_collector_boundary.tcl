set ::ot_ref_pre_cts 0
set_propagated_clock [get_clocks {core_clk w_*}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
# CLAUDE S81-DIE hub end / start block POST_CTS (make_sdc_hend.sh): each virtual IO clock at its own tree's measured
# WC insertion midpoint (vclk <- core_clk, vw <- the first w_* clock: the forwarded / second-domain tree), output min
# delay from the BC core tree (L - BC max - 25 ps, the S81-PH per-corner convention).
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
set ot_w ""
foreach c [get_clocks -quiet {w_*}] { set n [get_property $c full_name]; if {$ot_w eq "" || [string compare $n $ot_w] < 0} { set ot_w $n } }
foreach {c v} [list core_clk vclk $ot_w vw] {
  if {$c eq ""} { continue }
  set wc [ot_ins $c WC]
  if {[llength $wc] == 0} { puts "post_cts_hend: no $c latency"; continue }
  set L [expr {round(([lindex $wc 0] + [lindex $wc 1]) / 2.0)}]
  set_clock_latency $L [get_clocks $v]
  puts "post_cts_hend: $c WC $wc -> $v latency $L"
}

set_input_delay 166.667 -clock vw [get_ports {di*}]
set_input_delay -min 0 -clock vw [get_ports {di*}]
set_output_delay 316.667 -clock vclk [get_ports {o*}]
set_output_delay -min 0 -clock vclk [get_ports {o*}]
set_input_delay 166.667 -clock vclk [get_ports {xf*}]
set_input_delay -min 0 -clock vclk [get_ports {xf*}]
set_false_path -from [get_ports {rs*}]
