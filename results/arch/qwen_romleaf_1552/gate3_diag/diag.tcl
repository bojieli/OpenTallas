# Q-ROMPARENT diagnostic on gate3 4_1_cts.odb (TT, placement RC, 4_cts.sdc). Read-only.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_TT_*]] { read_liberty $f }
foreach f {physical/ref_tile/ot_qwen_tile_node/views/ot_qwen_tile_node/ot_qwen_tile_node_tt.lib
           physical/ref_tile/ot_qwen_tile_romleaf/views/ot_qwen_tile_romleaf/ot_qwen_tile_romleaf_tt.lib
           physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1/ot_qwen_tile_lsl_fp1_tt.lib} { read_liberty /src/$f }
read_db /in/4_1_cts.odb
read_sdc /in/4_cts.sdc
source $P/setRC.tcl
estimate_parasitics -placement
set o /out
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
# 1. every instance
set f [open $o/insts.tsv a]
puts $f "name\tmaster\tx\ty\tw\th\tseq\tblock\tclknet"
if {0} {foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set bb [$inst getBBox]
  set seq [expr {[$m isSequential] ? 1 : 0}]
  set blk [expr {[$m isBlock] ? 1 : 0}]
  set cn ""
  if {$seq} {
    foreach it [$inst getITerms] {
      if {[[$it getMTerm] getSigType] eq "CLOCK" || [string match -nocase CLK [[$it getMTerm] getName]]} {
        set n [$it getNet]; if {$n ne "NULL"} {set cn [$n getName]}
      }
    }
  }
  puts $f "[$inst getName]\t[$m getName]\t[expr {[$bb xMin]/double($dbu)}]\t[expr {[$bb yMin]/double($dbu)}]\t[expr {[$bb getDX]/double($dbu)}]\t[expr {[$bb getDY]/double($dbu)}]\t$seq\t$blk\t$cn"
}
close $f
}
puts "INSTS done"
# 2. clock tree: per root clock, every register clock pin with arrival
proc clk_arr {pin clock} {
  set clock_name [get_full_name $clock]
  set best ""
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator rise max]
    while {[$paths has_next]} {
      set path [$paths next]
      set tag [$path tag]
      if {[lindex $tag 3] ne $clock_name || [string first "(clock prop)" $tag] < 0} continue
      set best [sta::time_sta_ui [$path arrival]]
    }
    $paths finish
  }
  return $best
}
set f [open $o/sinks.tsv w]
puts $f "clock\tsources\tpin\tarrival_ps"
foreach clk [all_clocks] {
  if {[catch {set srcs [get_property $clk sources]}] || ![llength $srcs]} continue
  set src [get_full_name $srcs]
  set pins [all_registers -clock [get_full_name $clk] -clock_pins]
  foreach pin $pins {
    puts $f "[get_full_name $clk]\t$src\t[get_full_name $pin]\t[clk_arr $pin $clk]"
  }
}
close $f
puts "SINKS done"
# 3. clock buffers (tree structure): driver net name per clock buffer
set f [open $o/clkbufs.tsv w]
foreach net [$block getNets] {
  if {[$net getSigType] ne "CLOCK"} continue
  set d ""; foreach it [$net getITerms] { if {[$it isOutputSignal]} { set d [[$it getInst] getName] } }
  puts $f "[$net getName]\t$d\t[llength [$net getITerms]]"
}
close $f
# 4. setup paths
proc xy {pin} {
  set n [get_full_name $pin]
  if {[string first "/" $n] < 0} {
    set bt [[ord::get_db_block] findBTerm $n]
    if {$bt eq "NULL" || $bt eq ""} { return {-1 -1} }
    set bb [$bt getBBox]
    return [list [expr {([$bb xMin]+[$bb xMax])/2000.0}] [expr {([$bb yMin]+[$bb yMax])/2000.0}]]
  }
  set dp [sta::sta_to_db_pin $pin]
  if {$dp eq "" || $dp eq "NULL" || [catch {set r [$dp getAvgXY]}] || ![lindex $r 0]} {
    if {[catch {set bb [[$dp getInst] getBBox]}]} { return {-1 -1} }
    return [list [expr {([$bb xMin]+[$bb xMax])/2000.0}] [expr {([$bb yMin]+[$bb yMax])/2000.0}]]
  }
  return [list [expr {[lindex $r 1]/1000.0}] [expr {[lindex $r 2]/1000.0}]]
}
proc dump {paths fn} {
  set f [open $fn w]
  puts $f "slack_ps\tstart\tend\tstart_xy\tend_xy\tmanh_um\tpath_wire_um\tcells\tstart_clk\tend_clk\tlaunch_clk_ps\tcapture_clk_ps"
  foreach pe $paths {
    set pts [get_property $pe points]
    set wl 0.0; set prev ""; set cells 0
    foreach pt $pts {
      set pin [get_property $pt pin]
      set c [xy $pin]
      if {$prev ne "" && [lindex $c 0] >= 0 && [lindex $prev 0] >= 0} {
        set wl [expr {$wl + abs([lindex $c 0]-[lindex $prev 0]) + abs([lindex $c 1]-[lindex $prev 1])}]
      }
      set prev $c
      if {[sta::pin_direction $pin] eq "output"} { incr cells }
    }
    set sp [get_property $pe startpoint]; set ep [get_property $pe endpoint]
    set a [xy $sp]; set b [xy $ep]
    set m [expr {abs([lindex $a 0]-[lindex $b 0]) + abs([lindex $a 1]-[lindex $b 1])}]
    set sc [get_property $pe startpoint_clock]; set ec [get_property $pe endpoint_clock]
    puts $f "[format %.1f [expr {[get_property $pe slack]*1e12}]]\t[get_full_name $sp]\t[get_full_name $ep]\t$a\t$b\t[format %.1f $m]\t[format %.1f $wl]\t$cells\t[expr {$sc eq "" ? "-" : [get_name $sc]}]\t[expr {$ec eq "" ? "-" : [get_name $ec]}]"
  }
  close $f
}
report_tns > $o/summary.rpt
report_wns >> $o/summary.rpt
report_worst_slack -max >> $o/summary.rpt
report_worst_slack -min >> $o/summary.rpt
set mx [find_timing_paths -path_delay max -group_path_count 20000 -endpoint_path_count 1 -sort_by_slack -slack_max 0]
puts "setup violating endpoints: [llength $mx]"
dump $mx $o/setup_paths.tsv
set mn [find_timing_paths -path_delay min -group_path_count 5000 -endpoint_path_count 1 -sort_by_slack -slack_max 0.0]
puts "hold violating endpoints: [llength $mn]"
dump $mn $o/hold_paths.tsv
report_checks -path_delay max -group_path_count 8 -fields {fanout cap slew input_pins} -digits 1 > $o/setup_top.rpt
report_checks -path_delay max -to [get_ports {n_y[124]}] -fields {fanout cap slew input_pins} -digits 1 > $o/ny124.rpt
report_checks -path_delay max -to [get_pins -hierarchical {u_g.n_a_q[9]$_DFF_P_/D}] -fields {fanout cap slew input_pins} -digits 1 > $o/naq9.rpt
report_checks -path_delay min -group_path_count 5 -fields {fanout cap slew input_pins} -digits 1 > $o/hold_top.rpt
puts "END ok"
