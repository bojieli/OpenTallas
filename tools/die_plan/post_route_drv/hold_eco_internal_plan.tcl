# HOLD-FLOW-R 11-16: in-session planner for the targeted internal hold insert (OT_PRD_HOLD_TARGETED=1).  Same sizing as
# tools/die_plan/hold_eco_internal.py (a parity test runs both on one table): need = target - FF hold slack; one HB4 up to 25 ps
# of need, else ceil(need / 29.8) and at least two, at most 4; cut to what the endpoint's TT setup slack pays inside -42
# (132.8 ps per cell); port starts / output ends and non-capture pins never get a cell.
# ot_hei_size {need hb4_ff double_over cap}  -> cells
# ot_hei_afford {tt_ps hb4_tt floor}         -> cells the TT slack can pay
# ot_hei_auto_plan {ffargs ttargs out}       ffargs / ttargs = extra find_timing_paths args, e.g. {-scenes BC} {-scenes TC}
proc ot_hei_size {need {hb4_ff 29.8} {double_over 25.0} {cap 4}} {
  if {$need <= 0} { return 0 }
  set n [expr {int(ceil($need / $hb4_ff))}]
  if {$need > $double_over && $n < 2} { set n 2 }
  if {$n < 1} { set n 1 }
  if {$n > $cap} { set n $cap }
  return $n
}
proc ot_hei_afford {tt hb4_tt floor} {
  if {$tt <= $floor} { return 0 }
  return [expr {int(floor(($tt - $floor) / $hb4_tt))}]
}
proc ot_hei_capture_pin {name} {
  set pin [lindex [split $name /] end]
  return [expr {$pin in {D RESETN SETN} || [string match wd_in* $pin]}]
}
proc ot_hei_env {k d} { return [expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d}] }
proc ot_hei_auto_plan {ffargs ttargs out} {
  set target [ot_hei_env OT_HEI_TARGET_PS 10.0]; set hb4_ff [ot_hei_env OT_HEI_HB4_FF_PS 29.8]
  set hb4_tt [ot_hei_env OT_HEI_HB4_TT_PS 132.8]; set floor [ot_hei_env OT_HEI_TT_FLOOR_PS -42.0]
  set unit [sta::time_sta_ui 1e-12]          ;# one ps in the session's time unit
  set tt [dict create]
  foreach pe [find_timing_paths {*}$ttargs -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    dict set tt [get_full_name [get_property $pe endpoint]] [expr {[get_property $pe slack] / $unit}]
  }
  set worst [dict create]; set skipped 0; set negint 0
  foreach pe [find_timing_paths {*}$ffargs -path_delay min -slack_max [expr {$target * $unit}] -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    set en [get_full_name [get_property $pe endpoint]]; set sn [get_full_name [get_property $pe startpoint]]
    set sl [expr {[get_property $pe slack] / $unit}]
    if {[llength [get_ports -quiet $sn]] || [llength [get_ports -quiet $en]] || ![ot_hei_capture_pin $en]} { incr skipped; continue }
    if {$sl < 0} { incr negint }
    if {![dict exists $worst $en] || $sl < [dict get $worst $en]} { dict set worst $en $sl }
  }
  set fh [open $out w]
  puts $fh "# hold_eco_internal auto plan: capture_pin\tn_hb4"
  set cells 0; set eps 0; set cut 0; set none 0
  foreach en [lsort [dict keys $worst]] {
    set sl [dict get $worst $en]
    set n [ot_hei_size [expr {$target - $sl}] $hb4_ff 25.0 4]
    if {$n < 1} continue
    set ttv [expr {[dict exists $tt $en] ? [dict get $tt $en] : 1e6}]
    set a [ot_hei_afford $ttv $hb4_tt $floor]
    if {$a < 1} { incr none; puts $fh "# skipped $en: TT slack [format %.2f $ttv] cannot pay one cell"; continue }
    if {$a < $n} { incr cut; set n $a }
    puts $fh "$en\t$n"; incr cells $n; incr eps
  }
  puts $fh "# summary endpoints=$eps hb4=$cells partial=$cut tt_skipped=$none port_or_noncapture_skipped=$skipped negative_internal=$negint"
  close $fh
  puts "OT_HEI_PLAN endpoints=$eps hb4=$cells partial=$cut tt_skipped=$none port_or_noncapture_skipped=$skipped negative_internal=$negint"
  return $eps
}
