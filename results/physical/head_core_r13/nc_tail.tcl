# HEAD-CORE-R13 own NUMBER-CHECK: reg->reg worst slacks per group + clock-pin arrival census (own code)
puts "NC WS_MAX_clk [sta::worst_slack_cmd max]"
puts "NC WS_MIN_all [sta::worst_slack_cmd min]"
foreach g {clk vclk} {
  foreach d {max min} {
    set pe [find_timing_paths -path_group $g -path_delay $d -group_path_count 1]
    if {[llength $pe]} { puts "NC GROUP $g $d slack [get_property [lindex $pe 0] slack] ep [get_full_name [get_property [lindex $pe 0] endpoint]]" }
  }
}
set pe [find_timing_paths -path_delay min -group_path_count 100000 -slack_max 0]
puts "NC HOLD_NEG_ENDPOINTS [llength $pe]"
set n 0; set s 0.0; set mn 1e9; set mx -1e9; set err 0
foreach p [all_registers -clock_pins] {
  if {[catch {set a [get_property $p arrival_max_rise]} e]} { incr err; if {$err<2} {puts "NC ERR $e"}; continue }
  if {$a eq "" } { incr err; continue }
  set a [expr {double($a)}]
  incr n; set s [expr {$s+$a}]; if {$a<$mn} {set mn $a}; if {$a>$mx} {set mx $a}
}
if {$n} { puts "NC INS_MAXRISE n $n min [format %.2f $mn] mean [format %.2f [expr {$s/$n}]] max [format %.2f $mx] err $err" } else { puts "NC INS none err $err" }
