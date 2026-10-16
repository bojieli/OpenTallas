# Run only against the actual qcore CTS or routed timing session after native
# signoff SDC replay. Each query uses real clock roots; no fabricated endpoint.
# clk_ctl captures the raw input rung, then the next edge commits at each bank.
if {![info exists ::ot_ce_ports]} {error "native clock-entry signoff context required"}
set ctl_index [lsearch -exact $::ot_ce_ports clk_ctl]
if {$ctl_index < 0} {error "missing actual controller root"}
set ctl_clock [get_clocks ot_entry_$ctl_index]
set count 0
for {set b 0} {$b < 64} {incr b} {
  set name [format {clk_rf[%d]} $b]
  set index [lsearch -exact $::ot_ce_ports $name]
  if {$index < 0} {error "missing RF root $name"}
  set dest [get_clocks ot_entry_$index]
  foreach delay {max min} {
    set paths [find_timing_paths -from $ctl_clock -to $dest -path_delay $delay -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths]} {error "no actual ctl-to-bank $b $delay timing path"}
    set path [lindex $paths 0]
    puts [format {QCORE_CAPTURE bank=%d check=%s slack_ps=%.6f start=%s end=%s} $b $delay [get_property $path slack] [get_full_name [get_property $path startpoint]] [get_full_name [get_property $path endpoint]]]
    report_checks -from $ctl_clock -to $dest -path_delay $delay -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded
    incr count
  }
}
if {$count != 128} {error "incomplete native bank capture witness $count"}
puts "QCORE_CAPTURE COMPLETE 64 banks / 128 setup+hold checks"
