set ::ot_frame_clock_profile {{xk[0]} {ot_frame_xk0 {u_cf/C0} {u_xo0/CK} u_xo0/CKO {tt {{u_cf/C0} {10 20} {u_xo0/CK} {10 20}}}} {xk[1]} {ot_frame_xk1 {u_cf/C1} {u_xo1/CK} u_xo1/CKO {tt {{u_cf/C1} {10 20} {u_xo1/CK} {10 20}}}} {xk[2]} {ot_frame_xk2 {u_cf/C2} {u_xo2/CK} u_xo2/CKO {tt {{u_cf/C2} {10 20} {u_xo2/CK} {10 20}}}} {xk[3]} {ot_frame_xk3 {u_cf/C3} {u_xo3/CK} u_xo3/CKO {tt {{u_cf/C3} {10 20} {u_xo3/CK} {10 20}}}}}
proc ot_frame_clock_edge {pin clock transition delay} {
  set scene [get_property [sta::cmd_scene] name]
  set cname [get_full_name $clock]
  set edge [expr {$transition eq "rise" ? "^" : "v"}]
  set waveform [$clock waveform]
  set phase [sta::time_sta_ui [lindex $waveform [expr {$transition eq "rise" ? 0 : 1}]]]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator $transition $delay]
    while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; puts "TAG [get_full_name $pin] $transition $delay $tag"
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${edge}${delay}" ||
          [lindex $tag 3] ne $cname || [string first "(clock prop)" $tag] < 0} continue
      if {[lindex $tag 4] ne $edge} {
        $paths finish; error "OT_FRAME_CLOCK: inverted/unknown physical phase on [get_full_name $pin]"
      }
      set value [expr {[sta::time_sta_ui [$path arrival]] - $phase}]
      if {![string is double -strict $value] || [regexp -nocase {inf|nan} $value]} {
        $paths finish; error "OT_FRAME_CLOCK: nonfinite propagated clock arrival"
      }
      lappend values $value
    }
    $paths finish
  }
  if {[llength $values] != 1} {error "OT_FRAME_CLOCK: missing/ambiguous actual $delay $transition clock tag on [get_full_name $pin]"}
  return [lindex $values 0]
}
proc ot_frame_clock_audit {corner} {
  if {$corner ni {tt ff}} {error "OT_FRAME_CLOCK: actual TT or FF scene required"}
  sta::worst_slack_cmd max
  sta::worst_slack_cmd min
  set covered 0
  dict for {root row} $::ot_frame_clock_profile {
    lassign $row cname cf relay forwarded refs
    set clock [get_clocks -quiet $cname]
    if {[llength $clock] != 1} {error "OT_FRAME_CLOCK: missing/ambiguous actual root clock $cname"}
    set low 1e30; set high -1e30
    foreach endpoint [list $cf $relay] {
      set pin [get_pins -quiet $endpoint]
      if {[llength $pin] != 1} {error "OT_FRAME_CLOCK: missing child clock pin $endpoint"}
      lassign [dict get $refs $corner $endpoint] rlow rhigh
      foreach transition {rise fall} {
        set early [ot_frame_clock_edge $pin $clock $transition min]
        set late [ot_frame_clock_edge $pin $clock $transition max]
        if {$early > $late} {error "OT_FRAME_CLOCK: reversed actual clock arrival interval"}
        set low [expr {min($low,$early+$rlow)}]; set high [expr {max($high,$late+$rhigh)}]
      }
      incr covered
    }
    set output [get_pins -quiet $forwarded]
    if {[llength $output] != 1} {error "OT_FRAME_CLOCK: missing forwarding pin $forwarded"}
    foreach transition {rise fall} {
      set early [ot_frame_clock_edge $output $clock $transition min]
      set late [ot_frame_clock_edge $output $clock $transition max]
      puts "OT_FRAME_CLOCK FORWARD $corner $root $forwarded $transition $early $late"
    }
    set spread [expr {$high-$low}]
    puts "OT_FRAME_CLOCK PAIR $corner $root $cf $relay low=$low high=$high spread=$spread"
    if {$spread > 80.0} {error "OT_FRAME_CLOCK: actual linked-child boundary spread exceeds 80ps"}
  }
  if {$covered != 8} {error "OT_FRAME_CLOCK: incomplete actual child pin coverage $covered/8"}
  puts "OT_FRAME_CLOCK COVERAGE $corner PASS $covered/8"
}
