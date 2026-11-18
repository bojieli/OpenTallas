# FABLE-FIX-QC-N N4.1 (D) 11-18 (POST_CTS, sourced by the kit's cts_post.tcl after tap_balance.tcl, before the PG connect):
# hard clock-landing write clocks padded to their insertion target.  Table cland_fclk_targets.txt (gen_phys /
# cland_fclk_target.py): `inst pin port pin_delay_ps target_ps edge`; pin_delay_ps = the port -> cland pin clock delay that
# puts the capturing edge at input max + 45 ps data allowance + the cland lib setup.  CTS leaves the one-sink forwarded
# clock a bare wire (QC sle_st_a: 2.2 ps, 2,743 d pins -50..-66 ps).  Each pass measures the pin on the propagated clock
# (tap_balance.tcl tb_measure frame) and hangs BUFx4 delay cells in front of the pin (tb_hang at tb_outside, as the CP2
# core pass does for an early core pin).  Raise only: a pin already at or over its delay is left alone, nothing is removed.
proc cft_rows {path} {
  set out {}
  if {![file exists $path]} { return $out }
  set fh [open $path]
  foreach l [split [read $fh] "\n"] {
    if {[string match "#*" $l] || [llength $l] < 4} continue
    lappend out [lrange $l 0 5]
  }
  close $fh
  return $out
}
# delay cells for a shortfall d ps at `stage` ps a cell (>= 1); the last pass may overshoot by under one stage
proc cft_cells {d stage} { return [expr {max(1, int(ceil(double($d) / $stage)))}] }
# stage price after a pass that added nb cells and gained `gain` ps (kept within 10..60 ps)
proc cft_stage {gain nb old} {
  if {$nb <= 0 || $gain <= 0} { return $old }
  return [expr {min(60.0, max(10.0, double($gain) / $nb))}]
}
proc cft_delay {pin edge} {
  set clocks [get_property $pin clocks]
  if {[llength $clocks] != 1} { error "OT_CLAND_FCLK: missing unique clock at [get_full_name $pin]" }
  return [ot_cf_wire_transition $pin [lindex $clocks 0] $edge]
}
# FABLE-FIX-QC-STA 11-18: measured data.  The table delay assumes the cland d pins sit at their ports (45 ps data).  QC
# slw_st_a_v2 u_cland_b_hw_ctl_hc0_i (N-pin master, ports on the E face 175-372 um away) has 236 ps of port -> pin data:
# 1,574 d pins at -177 ps with the table delay met.  The delay a pin needs is the larger of the table value and what the
# worst d pin still lacks (arrival a - worst setup slack + 5 ps), capped at the table value + OT_CLAND_FCLK_DATA_CAP_PS (208).
proc cft_need {need a ds cap} {
  if {$ds eq "" || $ds >= 0} { return $need }
  return [expr {min($need + $cap, max($need, $a - $ds + 5.0))}]
}
proc cft_dslack {inst} {
  if {[catch {set pins [get_pins -quiet "$inst/d\[*\]"]}] || ![llength $pins]} { return "" }
  if {[catch {set pe [find_timing_paths -path_delay max -to $pins -group_path_count 1 -sort_by_slack]}] || ![llength $pe]} { return "" }
  return [sta::time_sta_ui [[lindex $pe 0] slack]]
}
proc cft_run {path} {
  global tb_added
  set rows [cft_rows $path]
  if {![llength $rows]} { return 0 }
  set blk [ord::get_db_block]
  set tol [expr {[info exists ::env(OT_CLAND_FCLK_TOL_PS)] ? $::env(OT_CLAND_FCLK_TOL_PS) : 3.0}]
  set stage {}; set first {}; set cells {}; set last {}
  set needx {}; set dcap [expr {[info exists ::env(OT_CLAND_FCLK_DATA_CAP_PS)] ? $::env(OT_CLAND_FCLK_DATA_CAP_PS) : 208.0}]
  for {set ps 0} {$ps < 5} {incr ps} {
    set_propagated_clock [all_clocks]
    estimate_parasitics -placement
    ot_cf_refresh
    set todo 0
    tb_begin
    foreach r $rows {
      lassign $r inst pin port need target edge
      if {$edge ni {rise fall}} { set edge rise }
      set p "$inst/$pin"
      set it [$blk findITerm $p]
      if {$it eq "NULL" || $it eq ""} { error "OT_CLAND_FCLK FAIL: cland clock pin $p (target table) is not in the design" }
      set sp [get_pins -quiet [string map {"\[" "\\\[" "\]" "\\\]"} $p]]
      if {$sp eq ""} { set sp [get_pins -quiet $p] }
      if {$sp eq ""} { error "OT_CLAND_FCLK FAIL: no STA pin $p" }
      set a [cft_delay $sp $edge]
      if {$a eq ""} { error "OT_CLAND_FCLK FAIL: no propagated $edge arrival at $p" }
      if {![dict exists $first $p]} { dict set first $p $a; dict set cells $p 0; dict set stage $p 30.0 }
      if {[dict exists $last $p]} {
        lassign [dict get $last $p] a0 nb0
        dict set stage $p [cft_stage [expr {$a - $a0}] $nb0 [dict get $stage $p]]
      }
      dict set last $p [list $a 0]
      set need [cft_need $need $a [cft_dslack $inst] $dcap]
      dict set needx $p $need
      set d [expr {$need - $a}]
      if {$d <= $tol} continue
      set nb [cft_cells $d [dict get $stage $p]]
      lassign [tb_outside $it] x y
      set tag "[regsub -all {[^A-Za-z0-9_]} $p _]_cft$ps"
      set n [tb_hang $it [$it getNet] $nb $tag $x $y]
      if {[info exists tb_added]} { incr tb_added $n }
      dict set cells $p [expr {[dict get $cells $p] + $n}]
      dict set last $p [list $a $n]
      set todo 1
    }
    tb_end $todo
    if {!$todo} break
  }
  set short 0
  foreach r $rows {
    lassign $r inst pin port need target edge
    set p "$inst/$pin"
    set a [lindex [dict get $last $p] 0]
    if {[dict exists $needx $p]} { set need [dict get $needx $p] }
    set st OK
    if {$a < $need - $tol} { set st "WARN short by [format %.1f [expr {$need - $a}]] ps"; incr short }
    puts "OT_CLAND_FCLK_TARGET $inst [format %.1f $target] pin_delay [format %.1f [dict get $first $p]] -> [format %.1f $a] ps (need [format %.1f $need], +[dict get $cells $p] cells) $st"
  }
  puts "OT_CLAND_FCLK done: [llength $rows] cland write clocks, $short short"
  return [llength $rows]
}
uplevel #0 { cft_run [file join [file dirname [file normalize [info script]]] cland_fclk_targets.txt] }
