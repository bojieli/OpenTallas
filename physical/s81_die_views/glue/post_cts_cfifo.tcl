# CLAUDE S81-RERUN dsfd_cfifo POST_CTS: each virtual IO clock at its own tree's measured WC insertion midpoint
# (vclk <- core_clk = ck, vw <- wclk = xf); output min delay from the BC column tree (L - BC max - 25 ps, the S81-PH
# per-corner convention), applied per output class so the rd falling-edge relation is kept.
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
foreach {c v} {core_clk vclk wclk vw} {
  set wc [ot_ins $c WC]
  if {[llength $wc] == 0} { puts "post_cts_cfifo: no $c latency"; continue }
  set L [expr {round(([lindex $wc 0] + [lindex $wc 1]) / 2.0)}]
  set_clock_latency $L [get_clocks $v]
  puts "post_cts_cfifo: $c WC $wc -> $v latency $L"
  if {$c eq "core_clk"} {
    set bc [ot_ins core_clk BC]
    if {[llength $bc]} {
      set omin [expr {$L - round([lindex $bc 1]) - 25}]
      set_output_delay -min $omin -clock vclk [get_ports {xa* xb* cc* rs*}]
      set_output_delay -min $omin -clock vclk -clock_fall [get_ports {rd*}]
      puts "post_cts_cfifo: BC $bc -> output min delay $omin"
    }
  }
}
