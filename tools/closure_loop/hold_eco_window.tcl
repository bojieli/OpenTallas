# closure-loop HOLD-ECO: per-endpoint IO / hold WINDOW analysis on the multi-corner session (sourced by hold_eco.tcl,
# or standalone after the same MCMM setup).  For every FF hold endpoint below the hold target hm:
#   H = FF hold slack, S = SS setup slack of the same pin, deficit d = hm - H.
#   infeasible : S + H < hm + accept_ss  (no delay fixes hold to hm while keeping setup >= the acceptance line: the
#                window the constraints leave is too narrow -> IO budget / RTL, never an ECO)
#   tight      : S <= d + filt          (fixable on paper, but the post-route margin is under filt ps: skipped by the ECO)
#   fixable    : otherwise
# proc ot_window {hm filt accept_ss tag} -> dict {fixable {pins} tight {pins} infeasible {pins}}; prints OT_WIN lines
proc ot_pin_class {pin} {
  set n [get_full_name $pin]
  if {[catch {set isport [expr {[get_property $pin is_port]}]}]} { set isport [expr {[string first / $n] < 0}] }
  if {$isport} { return "port" }
  return "pin"
}
# SS setup slack of an endpoint: this session's own (two-corner session) or the SS corner session's file (ff session)
proc ot_ss_of {ep} {
  if {[info exists ::ot_ss_slack]} {
    set n [get_full_name $ep]
    if {[dict exists $::ot_ss_slack $n]} { return [dict get $::ot_ss_slack $n] }
    return -1e6   ;# unknown in SS -> never buffered blind
  }
  set s [get_property $ep slack_max]; if {$s eq "INF" || $s eq ""} { set s 1e6 }
  return $s
}
proc ot_window {hm filt accept_ss tag} {
  set paths [find_timing_paths -path_delay min -scenes ff -slack_max $hm -group_path_count 1000000 -endpoint_path_count 1 -sort_by_slack]
  set res [dict create fixable {} tight {} infeasible {}]
  set cls [dict create]
  # read every path end BEFORE any pin slack query: a slack_max query re-searches and frees the PathEnd objects
  set rows {}
  foreach p $paths { lappend rows [list [get_property $p endpoint] [get_property $p slack] [get_full_name [get_property $p startpoint]] [ot_pin_class [get_property $p startpoint]]] }
  set npaths [llength $paths]; unset paths
  foreach r $rows {
    lassign $r ep h spn spk
    set s [ot_ss_of $ep]
    set d [expr {$hm - $h}]
    if {$s + $h < $hm + $accept_ss} { set k infeasible } elseif {$s <= $d + $filt} { set k tight } else { set k fixable }
    dict lappend res $k $ep
    # class key: start kind / end kind, bus names with indices folded
    regsub -all {\[[0-9]+\]} $spn {[*]} sn; regsub -all {\[[0-9]+\]} [get_full_name $ep] {[*]} en
    regsub {/[A-Z]+$} $sn {} sn
    set key "$k|$spk:$sn -> [ot_pin_class $ep]:$en"
    if {![dict exists $cls $key]} { dict set cls $key [list 0 1e9 1e9 -1e9] }
    lassign [dict get $cls $key] c hmin smin wmax
    dict set cls $key [list [incr c] [expr {min($hmin,$h)}] [expr {min($smin,$s)}] [expr {max($wmax,$s+$h)}]]
  }
  puts "OT_WIN $tag endpoints_below_hm $npaths fixable [llength [dict get $res fixable]] tight [llength [dict get $res tight]] infeasible [llength [dict get $res infeasible]] (hm $hm filt $filt accept_ss $accept_ss)"
  set n 0
  foreach key [lsort [dict keys $cls]] {
    lassign [dict get $cls $key] c hmin smin wmax
    if {[incr n] <= 40} { puts [format "OT_WIN_CLASS %s n=%d worst_hold=%.1f worst_setup=%.1f best_window=%.1f" $key $c $hmin $smin $wmax] }
  }
  return $res
}
