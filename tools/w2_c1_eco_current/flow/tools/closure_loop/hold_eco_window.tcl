# closure-loop HOLD-ECO: per-endpoint IO / hold WINDOW analysis on the multi-corner session (sourced by hold_eco.tcl,
# or standalone after the same MCMM setup).  For every FF hold endpoint below the hold target hm:
#   H = FF hold slack, S = SS setup slack of the same pin, deficit d = hm - H.
#   r = SS cost of one FF ps of hold delay (::ot_ss_ff_ratio, 2.4: ASAP7 BUFx2 12.3 ps FF / 29.3 ps SS)
#   infeasible : S - r (accept_ff - H) < accept_ss  (no delay brings hold to the acceptance line while keeping setup on
#                it: the window the constraints leave is too narrow -> IO budget / RTL, never an ECO)
#   tight      : S <= r d + filt        (reaching hm would leave under filt ps of setup: skipped by the ECO)
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
    return ""     ;# unknown in SS -> class "nodata", never buffered blind
  }
  set s [get_property $ep slack_max]; if {$s eq "INF" || $s eq ""} { set s 1e6 }
  return $s
}
if {![info exists ::ot_ss_ff_ratio]} { set ::ot_ss_ff_ratio 2.4 }
proc ot_window {hm filt accept_ss tag {accept_ff 15}} {
  set paths [find_timing_paths -path_delay min -scenes ff -slack_max $hm -group_path_count 1000000 -endpoint_path_count 1 -sort_by_slack]
  set res [dict create fixable {} tight {} infeasible {} nodata {}]
  set cls [dict create]
  # read every path end BEFORE any pin slack query: a slack_max query re-searches and frees the PathEnd objects
  set rows {}
  foreach p $paths { lappend rows [list [get_property $p endpoint] [get_property $p slack] [get_full_name [get_property $p startpoint]] [ot_pin_class [get_property $p startpoint]]] }
  set npaths [llength $paths]; unset paths
  foreach r $rows {
    lassign $r ep h spn spk
    set s [ot_ss_of $ep]
    set d [expr {$hm - $h}]
    # a hold delay of d ps at FF costs about r x d ps at SS (ASAP7 BUFx2: 12.3 ps FF / 29.3 ps SS -> r 2.4)
    set r $::ot_ss_ff_ratio
    if {$s eq ""} { set k nodata; set s -1e6 } elseif {$s - $r * ($accept_ff - $h) < $accept_ss} { set k infeasible } elseif {$s <= $r * $d + $filt} { set k tight } else { set k fixable }
    dict lappend res $k $ep
    # class key: start kind / end kind, bus names with indices folded
    regsub -all {\[[0-9]+\]} $spn {[*]} sn; regsub -all {\[[0-9]+\]} [get_full_name $ep] {[*]} en
    regsub {/[A-Z]+$} $sn {} sn
    set key "$k|$spk:$sn -> [ot_pin_class $ep]:$en"
    if {![dict exists $cls $key]} { dict set cls $key [list 0 1e9 1e9 -1e9] }
    lassign [dict get $cls $key] c hmin smin wmax
    dict set cls $key [list [incr c] [expr {min($hmin,$h)}] [expr {min($smin,$s)}] [expr {max($wmax,$s+$h)}]]
  }
  puts "OT_WIN $tag endpoints_below_hm $npaths fixable [llength [dict get $res fixable]] tight [llength [dict get $res tight]] infeasible [llength [dict get $res infeasible]] nodata [llength [dict get $res nodata]] (hm $hm filt $filt accept_ss $accept_ss accept_ff $accept_ff r $::ot_ss_ff_ratio)"
  set n 0
  foreach key [lsort [dict keys $cls]] {
    lassign [dict get $cls $key] c hmin smin wmax
    if {[incr n] <= 40} { puts [format "OT_WIN_CLASS %s n=%d worst_hold=%.1f worst_setup=%.1f best_window=%.1f" $key $c $hmin $smin $wmax] }
  }
  return $res
}
