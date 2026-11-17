# HOLD-SDC-1116 (COORD class fix, FLOW: HEAD hw3 / hw4: 460 of 491 sign-off hold violators were output-bank flops): every repair_timing -hold stage
# sees the sign-off output / input constraints.  Sign-off STA reads the kit's constraint.sdc (signoff.py discover); a hold repair stage that
# loaded another SDC (an ORFS stage SDC rewritten by write_sdc, an overlay) could miss the min IO budget (set_output_delay -min / set_input_delay
# -min) and "repair" against looser ports.  This file wraps ::repair_timing (idempotent): before every -hold phase it
#   1. hashes the golden SDC (OT_SIGNOFF_SDC_SHA from config.mk must match, else error HOLD-SDC-MISMATCH: the kit and sign-off differ),
#   2. writes the session's SDC and re-applies every golden set_input_delay / set_output_delay (-min and -max) the session lacks or has with
#      another value (a port-level compare; nothing else in the session is touched, no false path or latency is undone),
#   3. prints OT_HOLD_SDC stage ... sha ... io_golden N session_missing M reapplied M.
# Source it once per openroad session after the design and SDC are loaded: source [file join [file dirname [info script]] hold_sdc_guard.tcl]
proc ::ot_hsg_parse_io {text} {
  # -> dict {"<in|out> <min|max> <clock> <port>" value}; one golden / written line per port
  set d [dict create]
  foreach line [split $text "\n"] {
    set line [string trim $line]
    if {![regexp {^set_(input|output)_delay\s} $line -> dir]} continue
    set mm max
    if {[regexp {\s-min(\s|$)} $line]} { set mm min }
    set tgt ""; set head $line
    set bi [string first "\[" $line]
    if {$bi >= 0} { set tgt [string range $line $bi end]; set head [string range $line 0 [expr {$bi - 1}]] }
    set clk "-"; set val ""; set skip 0; set first 1
    foreach w $head {
      if {$first} { set first 0; continue }
      if {$skip} { set clk $w; set skip 0; continue }
      if {$w eq "-clock"} { set skip 1; continue }
      if {[string match -* $w] && ![string is double -strict $w]} continue
      if {$val eq "" && [string is double -strict $w]} { set val $w } elseif {$tgt eq ""} { set tgt $w }
    }
    if {$val eq "" || $tgt eq ""} continue
    if {[regexp {get_clocks\s+\{?([^\}\]\s]+)} $clk -> cc]} { set clk $cc }
    set ports {}
    if {[regexp {get_ports\s+(?:-\S+\s+)*\{?([^\}\]]*)\}?\]} $tgt -> pl]} { set ports $pl } elseif {[string match "*all_outputs*" $tgt]} { set ports ALL_OUT } elseif {[string match "*all_inputs*" $tgt]} { set ports ALL_IN } else { set ports $tgt }
    foreach p $ports { dict set d "$dir $mm $clk $p" [format %.4f $val] }
  }
  return $d
}
proc ::ot_hsg_expand {d} {
  # [all_outputs] / [all_inputs] of the golden = every port of the session, so it compares with the per-port lines write_sdc prints
  set o {}; set i {}
  if {[llength [info commands all_outputs]]} { foreach p [all_outputs] { lappend o [get_full_name $p] } }
  if {[llength [info commands all_inputs]]} { foreach p [all_inputs -no_clocks] { lappend i [get_full_name $p] } }
  set r [dict create]
  dict for {k v} $d {
    lassign $k dir mm clk p
    if {$p eq "ALL_OUT"} { foreach q $o { dict set r "$dir $mm $clk $q" $v } } elseif {$p eq "ALL_IN"} { foreach q $i { dict set r "$dir $mm $clk $q" $v } } else { dict set r $k $v }
  }
  return $r
}
proc ::ot_hold_sdc_guard {stage {golden ""}} {
  if {$golden eq ""} {
    # the kit's own constraint.sdc = what sign-off reads (signoff.py discover): /work/constraint.sdc in a kit session, else the stage's SDC / SDC_FILE env
    foreach c [list /work/constraint.sdc [expr {[info exists ::env(SDC)] ? $::env(SDC) : ""}] [expr {[info exists ::env(SDC_FILE)] ? $::env(SDC_FILE) : ""}] [file join $::ot_hsg_dir constraint.sdc]] {
      if {$c ne "" && [file isfile $c]} { set golden $c; break }
    }
  }
  if {![file isfile $golden]} { puts "OT_HOLD_SDC $stage skip (no golden SDC $golden)"; return }
  set fh [open $golden]; set gtext [read $fh]; close $fh
  set sha [string range [lindex [exec sha256sum $golden] 0] 0 15]
  if {[info exists ::env(OT_SIGNOFF_SDC_SHA)] && $::env(OT_SIGNOFF_SDC_SHA) ne "" && ![string match "$::env(OT_SIGNOFF_SDC_SHA)*" $sha] && ![string match "${sha}*" $::env(OT_SIGNOFF_SDC_SHA)]} {
    error "HOLD-SDC-MISMATCH stage $stage: golden SDC $golden sha $sha != kit OT_SIGNOFF_SDC_SHA $::env(OT_SIGNOFF_SDC_SHA) (repair and sign-off would read different constraints)"
  }
  set gio [::ot_hsg_expand [::ot_hsg_parse_io $gtext]]
  set tmp [file join [expr {[info exists ::env(TMPDIR)] ? $::env(TMPDIR) : "/tmp"}] "hsg_session_[pid].sdc"]
  set missing {}
  if {[catch {write_sdc -no_timestamp $tmp} err] && [catch {write_sdc $tmp} err2]} {
    puts "OT_HOLD_SDC $stage sha $sha io_golden [dict size $gio] session unreadable ($err2): golden IO re-applied whole"
    set sio [dict create]
  } else {
    set fh [open $tmp]; set stext [read $fh]; close $fh; file delete -force $tmp
    set sio [::ot_hsg_expand [::ot_hsg_parse_io $stext]]
  }
  dict for {k v} $gio {
    if {![dict exists $sio $k] || abs([dict get $sio $k] - $v) > 1e-3} { lappend missing $k }
  }
  set n 0
  if {[llength $missing]} {
    # the golden IO block again, whole and in file order: the end state is exactly the sign-off IO constraints (a port line after an all_outputs line wins as in the SDC)
    foreach line [split $gtext "\n"] {
      set l [string trim $line]
      if {[regexp {^set_(input|output)_delay\s} $l] && ![catch {uplevel #0 $l}]} { incr n }
    }
  }
  puts "OT_HOLD_SDC $stage sha $sha io_golden [dict size $gio] session_missing [llength $missing] reapplied_lines $n"
  return [llength $missing]
}
set ::ot_hsg_dir [file dirname [file normalize [info script]]]
if {![llength [info procs ::ot_hsg_rt_orig]] && [llength [info commands ::repair_timing]]} {
  rename ::repair_timing ::ot_hsg_rt_orig
  proc ::repair_timing {args} {
    if {[lsearch -exact $args -hold] >= 0 || ([lsearch -exact $args -setup] < 0)} { ::ot_hold_sdc_guard repair_timing }
    return [uplevel 1 [list ::ot_hsg_rt_orig {*}$args]]
  }
}
