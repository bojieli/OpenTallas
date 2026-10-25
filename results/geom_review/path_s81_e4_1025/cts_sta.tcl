# post-CTS STA at one corner on placement RC (kit RCX-calibrated setRC), vclk bound per corner (TT 250 / FF 202.5)
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
source /work/vclk_corner.tcl
ot_vclk_bind [expr {$C eq "FF" ? "ff" : "tt"}]
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
puts [format "STA %s setup_wns %.1f tns %.1f nviol %d | hold_wns %.1f tns %.1f nviol %d" $C \
  [expr {[sta::worst_slack_cmd max]*1e12}] [expr {[sta::total_negative_slack_cmd max]*1e12}] [sta::endpoint_violation_count max] \
  [expr {[sta::worst_slack_cmd min]*1e12}] [expr {[sta::total_negative_slack_cmd min]*1e12}] [sta::endpoint_violation_count min]]
foreach g {clk vclk asynchronous} {
  foreach mm {max min} {
    set p [find_timing_paths -path_group $g -path_delay $mm -group_path_count 1]
    if {[llength $p]} { puts [format "STA %s group %s %s worst %.1f end %s" $C $g $mm [expr {[get_property [lindex $p 0] slack]*1e12}] [get_full_name [get_property [lindex $p 0] endpoint]]] }
  }
}
# clock: every register clock pin, per tap net
set b [ord::get_db_block]
set all {}
foreach p [all_registers -clock_pins] { if {![catch {set a [get_property $p arrival_max_rise]}] && $a ne ""} { lappend all [expr {$a*1e12 > 1e3 ? $a : $a}] } }
set all [lsort -real $all]
puts [format "CLK %s regs %d ins min %.1f max %.1f" $C [llength $all] [expr {[lindex $all 0]}] [expr {[lindex $all end]}]]
report_checks -path_delay max -group_path_count 5 -endpoint_path_count 1 > /work/e4_cts_${c}_max.rpt
report_checks -path_delay min -group_path_count 5 -endpoint_path_count 1 > /work/e4_cts_${c}_min.rpt
# per-tap sink dump: tap id, sink inst, x, y, arrival (corner)
proc sk {net} {
  set out {}; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue; dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set i [$it getInst]
      if {[regexp {^(BUF|INV|CKINV|HB)} [[$i getMaster] getName]]} {
        foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out $it }
    }
  }
  return $out
}
set fh [open /work/e4_taps_${c}.tsv w]
puts $fh "tap\tinst\tx\ty\tarr_ps\tmacro"
set u [$b getDbUnitsPerMicron]
foreach i [$b getInsts] {
  if {![regexp {^ot_dtap_(\d+)$} [$i getName] -> k]} continue
  set on ""; foreach o [$i getITerms] { if {[$o isOutputSignal]} { set on [$o getNet] } }
  foreach it [sk $on] {
    set s [$it getInst]; set bb [$s getBBox]
    set p [get_pins -quiet "[$s getName]/[[$it getMTerm] getName]"]
    set a -1; if {$p ne "" && ![catch {set a [get_property $p arrival_max_rise]}] && $a eq ""} { set a -1 }
    puts $fh [format "%s\t%s\t%.2f\t%.2f\t%s\t%d" $k [$s getName] [expr {([$bb xMin]+[$bb xMax])/2.0/$u}] [expr {([$bb yMin]+[$bb yMax])/2.0/$u}] $a [[$s getMaster] isBlock]]
  }
}
close $fh
puts "TAPDUMP done"
