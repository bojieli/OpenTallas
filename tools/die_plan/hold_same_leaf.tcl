# HOLD-SAMELEAF-1 (FABLE-OPEN-S81-A 11-23, S81 rc35).  The reg-to-reg family hold margin (HOLD-MARGIN-FAMILY) covers route-time
# skew between clock branches.  Two registers on the SAME clock leaf net (and a register feeding itself, Q -> mux -> D) have no
# unshared clock path: their hold cannot move with the clock route.  S81 slice C lepe_nh_mus_C: 13,664 of 33,593 hold cells
# padded such pairs (5,287 self-loops), in the congested bank pocket.  The scope below takes the paths between the registers of
# one leaf net out of the family-margin pass only: set_false_path -hold -from <registers of the leaf> -to <the same registers>,
# one exception per leaf (clock pins to data pins).  They keep the base margin (the all-paths pass before it), every other pair keeps the family target,
# and the hold GATE (FF hold >= 0 on every path at the SDC uncertainty) is unchanged.  The constraints are restored by removing
# the exceptions and replaying the SDC written before them, then compared (the form ot_hold_repair_scope uses).
# registers per clock leaf net: {{clock pin names} {other input pin names}} per net; standard-cell sequentials only (a hard
# macro has its own insertion)
proc pg_sl_groups {} {
  set out {}
  foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] ne "CLOCK"} continue
    set cks {}; set ds {}
    foreach t [$net getITerms] {
      if {![$t isInputSignal]} continue
      set i [$t getInst]; set m [$i getMaster]
      if {[$m isBlock] || ![$m isSequential]} continue
      set ckm [[$t getMTerm] getName]
      lappend cks "[$i getName]/$ckm"
      foreach d [$i getITerms] {
        if {[$d isInputSignal] && [[$d getMTerm] getName] ne $ckm && [$d getNet] ne "NULL"} { lappend ds "[$i getName]/[[$d getMTerm] getName]" }
      }
    }
    if {[llength $cks]} { lappend out [list $cks $ds] }
  }
  return $out
}
proc pg_sl_pins {names} {
  set ps {}
  foreach n $names { set p [get_pins -quiet $n]; if {[llength $p] == 1} { lappend ps [lindex $p 0] } }
  return $ps
}
proc pg_sl_modes {} { expr {[llength [info commands sta::cmd_mode_name]] && ([info exists ::pg_two] && $::pg_two || [info exists ::ot_mm_synced])} }
proc pg_sl_read {path} { set fh [open $path r]; try { return [read $fh] } finally { close $fh } }
# begin / end of one margin pass (call both in the FF hold mode): `margin` is the pass target, `base` the margin these pairs keep
proc pg_sl_begin {tag margin base} {
  set ::pg_sl_sets {}
  if {$margin <= $base} { return 0 }
  set t0 [clock seconds]; set n 0
  set dir [expr {[info exists ::env(RESULTS_DIR)] && [file isdirectory $::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [file dirname [file normalize [info script]]]}]
  set ::pg_sl_sdc [file join $dir pg_same_leaf_[pid]_[clock clicks].sdc]
  write_sdc -digits 17 -no_timestamp $::pg_sl_sdc
  foreach g [pg_sl_groups] {
    set f [pg_sl_pins [lindex $g 0]]; set t [pg_sl_pins [lindex $g 1]]
    if {![llength $f] || ![llength $t]} continue
    set_false_path -hold -from $f -to $t
    lappend ::pg_sl_sets [list $f $t]; incr n [llength $f]
  }
  puts "$tag same-leaf: $n registers on [llength $::pg_sl_sets] clock leaf nets keep margin $base in the margin $margin pass (paths inside one leaf net excepted), secs [expr {[clock seconds] - $t0}]"
  return $n
}
proc pg_sl_end {} {
  if {![info exists ::pg_sl_sdc]} return
  foreach c $::pg_sl_sets { unset_path_exceptions -hold -from [lindex $c 0] -to [lindex $c 1] }
  set ::pg_sl_sets {}
  set before $::pg_sl_sdc; unset ::pg_sl_sdc
  if {[pg_sl_modes]} { read_sdc -mode [sta::cmd_mode_name] $before } else { read_sdc $before }
  write_sdc -digits 17 -no_timestamp $before.after
  if {[pg_sl_read $before] ne [pg_sl_read $before.after]} { error "same-leaf scope restore differs: retained $before $before.after" }
  file delete $before $before.after
}
# GRT / route stage (hold_guard_grt.tcl sources this file when the kit says OT_HOLD_SAME_LEAF = 1): every hold repair there ends
# in the repair_timing command with the family margin (OT_HOLD_FF_MARGIN), which would pad the same pairs again.  The wrapper
# runs each hold repair whose -hold_margin is above the base margin (OT_HOLD_SAME_LEAF_BASE, default 5) inside the scope, removes
# the scope (also on error), then repairs once more at the base margin so a same-leaf pair below it is still repaired.  Any other
# call passes through untouched; if the scope cannot be applied the call runs as before.
proc pg_sl_install {} {
  if {[llength [info commands ::pg_sl_repair_timing_orig]] || ![llength [info commands ::repair_timing]]} { return 0 }
  rename ::repair_timing ::pg_sl_repair_timing_orig
  proc ::repair_timing {args} {
    set base [expr {[info exists ::env(OT_HOLD_SAME_LEAF_BASE)] && [string is double -strict $::env(OT_HOLD_SAME_LEAF_BASE)] ? $::env(OT_HOLD_SAME_LEAF_BASE) : 5.0}]
    set j [lsearch -exact $args -hold_margin]
    set hm [expr {$j >= 0 ? [lindex $args [expr {$j + 1}]] : ""}]
    set hold [expr {[lsearch -exact $args -hold] >= 0 || [lsearch -exact $args -setup] < 0}]
    if {!$hold || ![string is double -strict $hm] || $hm <= $base} { return [uplevel 1 [list ::pg_sl_repair_timing_orig {*}$args]] }
    set two [pg_sl_modes]
    if {$two} { set entry [sta::cmd_mode_name]; set_mode ff }
    set applied 0
    try {
      set applied [pg_sl_begin OT_HOLD_SAME_LEAF $hm $base]
    } on error {e} {
      puts "OT_HOLD_SAME_LEAF not applied ($e)"; set applied 0
      foreach c $::pg_sl_sets { catch {unset_path_exceptions -hold -from [lindex $c 0] -to [lindex $c 1]} }
      set ::pg_sl_sets {}; unset -nocomplain ::pg_sl_sdc
    } finally {
      if {$two} { set_mode $entry }
    }
    if {!$applied} { unset -nocomplain ::pg_sl_sdc; return [uplevel 1 [list ::pg_sl_repair_timing_orig {*}$args]] }
    try {
      set r [uplevel 1 [list ::pg_sl_repair_timing_orig {*}$args]]
    } finally {
      if {$two} { set entry [sta::cmd_mode_name]; set_mode ff }
      try { pg_sl_end } finally { if {$two} { set_mode $entry } }
    }
    # hold-only base pass for what the scope hid
    set bargs {}
    foreach a [lreplace $args [expr {$j + 1}] [expr {$j + 1}] $base] { if {$a ne "-setup"} { lappend bargs $a } }
    if {[lsearch -exact $bargs -hold] < 0} { lappend bargs -hold }
    uplevel 1 [list ::pg_sl_repair_timing_orig {*}$bargs]
    return $r
  }
  return 1
}
