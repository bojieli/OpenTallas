# rck_early_report.tcl -- PLAN-READERS-1 11-14 (FABLE-PLAN-B6B 6.4).  Sourced at the end of postcts_gate.tcl when the kit has
# /work/rck_early.txt (plan min_early_ps, pad_clock.write_contract; rows "entry inst pin min_early_ps").  For every row it
# prints the MEASURED lead of the macro clock pin over the earliest register clock pin of the same clock:
#   lead = min over register CK pins (arrival) - arrival of inst/pin       [ps, propagated clocks, the gate's parasitics]
#   OT_RCK_EARLY <entry> <inst>/<pin> lead <ps> min <ps> PASS|SHORT        one line per row, then OT_RCK_EARLY_SUMMARY
# REPORT ONLY (academic profile, OWNER 11-13): SHORT never changes the gate verdict or the exit status.
proc ot_rck_early_report {file corner} {
  set rows {}
  set fh [open $file]
  foreach ln [split [read $fh] "\n"] {
    set ln [string trim $ln]
    if {$ln eq "" || [string index $ln 0] eq "#"} continue
    lappend rows [split $ln " "]
  }
  close $fh
  set nshort 0
  set out {}
  foreach r $rows {
    lassign $r entry inst pin need
    set p [get_pins -quiet "$inst/$pin"]
    if {![llength $p]} { puts "OT_RCK_EARLY $entry $inst/$pin not in the block (SHORT)"; incr nshort; continue }
    set a [get_property $p arrival_max_rise]
    set clks [get_property $p clocks]
    if {![string is double -strict $a] || ![llength $clks]} { puts "OT_RCK_EARLY $entry $inst/$pin untimed (SHORT)"; incr nshort; continue }
    set a [expr {$a * 1e12}]
    set rmin ""
    foreach c $clks {
      foreach rp [all_registers -clock_pins -clock $c] {
        set ra [get_property $rp arrival_max_rise]
        if {![string is double -strict $ra]} continue
        set ra [expr {$ra * 1e12}]
        if {$rmin eq "" || $ra < $rmin} { set rmin $ra }
      }
    }
    if {$rmin eq ""} { puts "OT_RCK_EARLY $entry $inst/$pin no register clock pin timed (SHORT)"; incr nshort; continue }
    set lead [expr {$rmin - $a}]
    set v [expr {$lead + 1e-9 >= $need ? "PASS" : "SHORT"}]
    if {$v eq "SHORT"} { incr nshort }
    puts [format "OT_RCK_EARLY %s %s/%s corner %s lead %.1f min %.1f %s" $entry $inst $pin $corner $lead $need $v]
    lappend out [format "{\"entry\": \"%s\", \"pin\": \"%s/%s\", \"lead_ps\": %.2f, \"min_ps\": %.2f, \"verdict\": \"%s\"}" $entry $inst $pin $lead $need $v]
  }
  set fo [open /work/rck_early_report_[string tolower $corner].json w]
  puts $fo "\[[join $out ,\n ]\]"
  close $fo
  puts "OT_RCK_EARLY_SUMMARY corner $corner rows [llength $rows] short $nshort (report only, not a gate)"
}
