# CLAUDE S81-RERUN meso view POST_CTS: each virtual IO clock at its own clock tree's measured WC insertion midpoint;
# output min delay = L - (BC max insertion + 25 ps) (the S81-PH per-corner convention, vclk_latency.tcl).
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
foreach {c v outs} {wclk vw {w_rdy w_live w_fault} rclk vr {r_v r_d* r_live r_fault}} {
  set wc [ot_ins $c WC]; set bc [ot_ins $c BC]
  if {[llength $wc] == 0} { puts "meso post_cts: no $c latency"; continue }
  set L [expr {round(([lindex $wc 0] + [lindex $wc 1]) / 2.0)}]
  set_clock_latency $L [get_clocks $v]
  if {[llength $bc]} { set_output_delay -min [expr {$L - round([lindex $bc 1]) - 25}] -clock $v [get_ports $outs] }
  puts "meso post_cts: $c WC $wc BC $bc -> $v latency $L"
}
