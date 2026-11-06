# KW-FIX-17 11-05 (COORD 17:2x (5), estimate 18:06 (A)): targeted PRD fanout cap.  The default PRD session has no
# fanout limit (FLOW-CLOCK-R8: a blanket max_fanout 24 split bdring's 56-load nets and cost 17 ps TT setup).  The 72-h
# sign-off census found DRV violators that sit on high-fanout repair-buffer nets (wire*/load_slew*/place*, fo 50-193)
# where repair_design only resizes and the slew comes back after DRT.  Here, before the normal repair, only the signal
# nets that carry a max_slew / max_capacitance violator in this session AND drive more than OT_PRD_AUTO_FANOUT
# (default 32) loads get one repair_design with that max_fanout; every other net is guarded (DoNotTouch) during that
# call and restored afterwards (also on error), and the cap is reset.  A kit without such a net is untouched.
# OT_PRD_AUTO_FANOUT=0 = off.  An explicit OT_PRD_MAX_FANOUT (design-wide cap) or OT_PRD_TARGET_FANOUT wins.
# Sign-off limits and checks unchanged.
proc ot_prd_afo_key {name} { return [string map {\\ {}} $name] }
proc ot_prd_afo_loads {net} {
  set n 0
  foreach it [$net getITerms] { if {[$it isInputSignal]} { incr n } }
  foreach bt [$net getBTerms] { if {[$bt getIoType] eq "OUTPUT"} { incr n } }
  return $n
}
proc ot_prd_auto_fanout {drv_args limit} {
  if {![string is integer -strict $limit] || $limit < 0} { error "OT_PRD_AUTO_FANOUT invalid: $limit" }
  if {$limit == 0} { return 0 }
  set report [file join $::env(REPORTS_DIR) ot_prd_autofo.rpt]
  report_check_types -max_slew -max_capacitance -violators -max_count 100000 > $report
  set f [open $report]; set text [read $f]; close $f
  set vio [dict create]
  foreach line [split $text "\n"] {
    if {![regexp {^\s*(\S+)\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+-[0-9.eE+]+\s+\(VIOLATED\)} $line -> pin]} continue
    set objects [get_pins -quiet $pin]
    if {![llength $objects]} { set objects [get_ports -quiet $pin] }
    foreach net [get_nets -quiet -of_objects $objects] { dict set vio [ot_prd_afo_key [get_full_name $net]] 1 }
  }
  set sel {}; set others {}
  foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} continue
    if {[dict exists $vio [ot_prd_afo_key [$net getName]]] && [ot_prd_afo_loads $net] > $limit} {
      lappend sel "[$net getName]:[ot_prd_afo_loads $net]"
    } else {
      lappend others $net
    }
  }
  if {![llength $sel]} {
    puts "OT_PRD_AUTOFO none: [dict size $vio] violator nets, none above $limit loads (no fanout cap)"
    return 0
  }
  foreach net $others { $net setDoNotTouch 1 }
  puts "OT_PRD_AUTOFO max_fanout $limit on [llength $sel] violator nets above $limit loads (others guarded): [lrange $sel 0 49]"
  try { set_max_fanout $limit [current_design]; repair_design {*}$drv_args } finally {
    set_max_fanout 1e6 [current_design]
    foreach net $others { $net setDoNotTouch 0 }
  }
  return [llength $sel]
}
