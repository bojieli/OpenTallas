# HOLD-FLOW-R 11-16: in-session planner for the targeted internal hold insert (OT_PRD_HOLD_TARGETED=1).  Same sizing as
# tools/die_plan/hold_eco_internal.py (a parity test runs both on one table): need = target - FF hold slack; one HB4 up to 25 ps
# of need, else ceil(need / 29.8) and at least two, at most 4; cut to what the endpoint's TT setup slack pays inside -42
# (132.8 ps per cell); port starts / output ends and non-capture pins never get a cell.
# ot_hei_size {need hb4_ff double_over cap}  -> cells
# ot_hei_afford {tt_ps hb4_tt floor}         -> cells the TT slack can pay
# Selection (HOLD-FLOW-R 11-16, COORD): the endpoints that FAIL (slack < 0) plus a guard band (OT_HEI_SELECT_PS, default 2 ps: a
# re-extraction flips them), NOT everything under the +10 ps sizing target (1,440 endpoints picked for 1 failing).  Each selected
# endpoint is still sized to reach +target.
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
proc ot_hei_capture_pin {name {kind reg}} {
  set pin [lindex [split $name /] end]
  return [expr {$kind eq "macro" || $pin in {D RESETN SETN} || [string match wd_in* $pin]}]
}
# A timing-path endpoint supplies the capture obligation; names such as gsel[8] and ADDR are valid macro inputs.
# OpenDB confirms these are ordinary signal inputs, excluding clock/PG/output pins rather than guessing their names.
proc ot_hei_pin_info {name} {
  if {[llength [get_ports -quiet $name]]} { return [list port ""] }
  set kind reg; set net ""
  set pins [get_pins -quiet $name]
  if {[llength $pins] == 1 && ![catch {sta::sta_to_db_pin $pins} it] && $it ni {"" NULL}} {
    set n [$it getNet]
    if {$n ne "NULL"} { set net [$n getName] }
    if {[[$it getInst] getMaster] ne "NULL" && [[[$it getInst] getMaster] isBlock]} {
      if {![$it isInputSignal] || [[$it getMTerm] getSigType] ne "SIGNAL"} { return [list other $net] }
      set kind macro
    }
  }
  return [list $kind $net]
}
proc ot_hei_env {k d} { return [expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d}] }
proc ot_hei_auto_plan {ffargs ttargs out} {
  set select [ot_hei_env OT_HEI_SELECT_PS 2.0]; set target [ot_hei_env OT_HEI_TARGET_PS 10.0]; set hb4_ff [ot_hei_env OT_HEI_HB4_FF_PS 29.8]
  set hb4_tt [ot_hei_env OT_HEI_HB4_TT_PS 132.8]; set floor [ot_hei_env OT_HEI_TT_FLOOR_PS -42.0]
  set unit [sta::time_sta_ui 1e-12]          ;# one ps in the session's time unit
  set tt [dict create]
  foreach pe [find_timing_paths {*}$ttargs -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    dict set tt [get_full_name [get_property $pe endpoint]] [expr {[get_property $pe slack] / $unit}]
  }
  set worst [dict create]; set skipped 0; set negint 0; set info [dict create]; set ff [dict create]
  foreach pe [find_timing_paths {*}$ffargs -path_delay min -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
    set en [get_full_name [get_property $pe endpoint]]; set sn [get_full_name [get_property $pe startpoint]]
    set sl [expr {[get_property $pe slack] / $unit}]
    lassign [ot_hei_pin_info $en] kind net
    if {[llength [get_ports -quiet $sn]] || $kind ni {reg macro} || ![ot_hei_capture_pin $en $kind]} { incr skipped; continue }
    dict set info $en [list $kind $net]
    if {![dict exists $ff $en] || $sl < [dict get $ff $en]} { dict set ff $en $sl }
    if {$sl >= $select} continue
    if {$sl < 0} { incr negint }
    if {![dict exists $worst $en] || $sl < [dict get $worst $en]} { dict set worst $en $sl }
  }
  set fh [open $out w]
  puts $fh "# hold_eco_internal auto plan: capture_pin\tn_hb4"
  set none 0; set cut 0; set sel [dict create]; set selnet [dict create]; set lines {}; set notes {}
  foreach en [lsort [dict keys $worst]] {
    set sl [dict get $worst $en]
    set n [ot_hei_size [expr {$target - $sl}] $hb4_ff 25.0 4]
    if {$n < 1} continue
    set ttv [expr {[dict exists $tt $en] ? [dict get $tt $en] : 1e6}]
    set a [ot_hei_afford $ttv $hb4_tt $floor]
    if {$a < 1} { incr none; lappend notes "# skipped $en: TT slack [format %.2f $ttv] cannot pay one cell"; continue }
    if {$a < $n} { incr cut; set n $a }
    lassign [dict get $info $en] kind net
    dict set sel $en [list $n $kind $net]
  }
  # SHARED NETS (bksel 11-17): padding some sinks of a net and re-routing it cost the unpadded sink 14 ps.  Per touched net: pad EVERY
  # capture sink or none; a sibling gets max(1, cells for its own need) cut to its TT room; one that cannot pay a cell drops the net.
  set pad [ot_hei_env OT_HEI_PAD_SIBLINGS 1]; set dropped 0
  if {$pad ne "0"} {
    set nets [dict create]
    dict for {en v} $sel { if {[lindex $v 2] ne ""} { dict set nets [lindex $v 2] 1 } }
    foreach net [lsort [dict keys $nets]] {
      set add {}; set ok 1
      foreach en [lsort [dict keys $ff]] {
        lassign [dict get $info $en] kind n2
        if {$n2 ne $net || [dict exists $sel $en]} continue
        set sl [dict get $ff $en]
        set ttv [expr {[dict exists $tt $en] ? [dict get $tt $en] : 1e6}]
        set a [ot_hei_afford $ttv $hb4_tt $floor]
        if {$a < 1} { set ok 0; lappend notes "# skipped $en: net $net sibling cannot pay one cell (TT [format %.2f $ttv]); the whole net is left unpadded"; break }
        set n [ot_hei_size [expr {$target - $sl}] $hb4_ff 25.0 4]
        if {$n < 1} { set n 1 }
        if {$n > $a} { set n $a }
        lappend add [list $en $n $kind $net]
      }
      if {$ok} {
        foreach x $add { dict set sel [lindex $x 0] [lrange $x 1 3] }
      } else {
        incr dropped
        foreach en [dict keys $sel] { if {[lindex [dict get $sel $en] 2] eq $net} { dict unset sel $en; lappend notes "# skipped $en: net $net left unpadded: a sibling sink cannot be padded" } }
      }
    }
  }
  set cells 0; set eps 0; set touched [dict create]; set uncovered 0
  foreach en [lsort [dict keys $sel]] {
    lassign [dict get $sel $en] n kind net
    set tag [expr {$kind eq "macro" ? "\tmacro" : ""}]
    puts $fh "$en\t$n$tag"; incr cells $n; incr eps
    if {$net ne ""} { dict set touched $net 1 } else { incr uncovered }
  }
  foreach l $notes { puts $fh $l }
  set siblings 0
  dict for {en sl} $ff {
    lassign [dict get $info $en] kind net
    if {![dict exists $sel $en] && $net ne "" && [dict exists $touched $net]} {
      puts $fh "# reroute sibling $en net=$net ff_ps=[format %.3f $sl]; post-route hold must be measured"
      incr siblings
    }
  }
  puts $fh "# summary endpoints=$eps hb4=$cells partial=$cut tt_skipped=$none port_or_noncapture_skipped=$skipped negative_internal=$negint unmodified_touched_siblings=$siblings net_unmeasured=$uncovered nets_left_unpadded=$dropped"
  close $fh
  puts "OT_HEI_PLAN endpoints=$eps hb4=$cells partial=$cut tt_skipped=$none port_or_noncapture_skipped=$skipped negative_internal=$negint unmodified_touched_siblings=$siblings net_unmeasured=$uncovered nets_left_unpadded=$dropped"
  return $eps
}
