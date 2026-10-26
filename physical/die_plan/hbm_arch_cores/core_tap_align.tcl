# core_tap_align.tcl -- POST_CTS hook (HBM-CLKSTRUCT 2026-10-25), runs before the kit's tap_balance.tcl report.
# Balances the density-tap trees of core_density_taps.tcl: measures every tap's mean sink insertion (propagated clock,
# placement RC, CTS corner) and hangs a delay chain in front of each EARLY tap buffer (trunk -> delay cells -> tap)
# until all tap means sit within OT_DTAP_TOL_PS (default 8) of the latest tap -- the owner 10-23 rule "taps balanced
# to <= 20 ps" made explicit instead of trusting TritonCTS level balancing (measured 476..519 / 528..608 ps).
# env: OT_DTAP_TOL_PS, OT_DTAP_DELAY_CELL (default BUFx4_ASAP7_75t_R), OT_DTAP_ROUNDS (default 4), OT_DTAP_NEXT
# (script sourced at the end, default /work/tap_balance.tcl).
if {![llength [info commands ot_cf_wire]]} { source [file join [file dirname [info script]] clock_family.tcl] }
uplevel #0 {
set ta_blk [ord::get_db_block]
set ta_tol [expr {[info exists ::env(OT_DTAP_TOL_PS)] ? $::env(OT_DTAP_TOL_PS) : 8.0}]
set ta_cell [expr {[info exists ::env(OT_DTAP_DELAY_CELL)] ? $::env(OT_DTAP_DELAY_CELL) : "BUFx4_ASAP7_75t_R"}]
set ta_rounds [expr {[info exists ::env(OT_DTAP_ROUNDS)] ? $::env(OT_DTAP_ROUNDS) : 4}]
set ta_master [[ord::get_db] findMaster $ta_cell]
proc ta_isbuf {i} { return [regexp {^(BUF|INV|CKINV|HB)} [[$i getMaster] getName]] }
proc ta_sinks {net} {
  set out {}; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[ta_isbuf $i]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out "[$i getName]/[[$it getMTerm] getName]" }
    }
  }
  return $out
}
proc ta_measure {} {
  global ta_blk
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
  ot_cf_refresh
  set clk [lindex [all_clocks] 0]
  set res [dict create]
  foreach i [$ta_blk getInsts] {
    set n [$i getName]
    if {![regexp {^ot_dtap_[0-9]+$} $n]} continue
    set y [$i findITerm Y]; set net [$y getNet]
    set s 0.0; set k 0; set mn 1e9; set mx 0.0
    foreach p [ta_sinks $net] {
      set pin [get_pins -quiet $p]; if {$pin eq ""} continue
      # clock_family tagged arrival; a pin it cannot resolve uniquely falls back to the rise arrival property (the
      # core clk port carries no input delay, so a CK pin holds clock arrivals only)
      if {[catch {set a [ot_cf_wire $pin $clk]}] || $a eq ""} {
        if {[catch {set a [get_property $pin arrival_max_rise]}] || $a eq "" || $a eq "INF"} continue
      }
      set s [expr {$s + $a}]; incr k; set mn [expr {min($mn, $a)}]; set mx [expr {max($mx, $a)}]
    }
    if {$k} { dict set res $n [list [expr {$s / $k}] $mn $mx $k] }
  }
  return $res
}
proc ta_line {tag m} {
  set l $tag; set lo 1e9; set hi 0
  dict for {n v} $m { set lo [expr {min($lo, [lindex $v 0])}]; set hi [expr {max($hi, [lindex $v 0])}]; append l " [string range $n 8 end]=[format %.0f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]])" }
  return "$l | tap means [format %.1f $lo]..[format %.1f $hi] spread [format %.1f [expr {$hi - $lo}]] ps"
}
# one delay cell in front of tap inst (between its current input net and its A pin), placed at the tap
proc ta_add {tap r b} {
  global ta_blk ta_master
  set a [$tap findITerm A]; set src [$a getNet]
  set inst [odb::dbInst_create $ta_blk $ta_master "[$tap getName]_al${r}_$b"]
  set nn [odb::dbNet_create $ta_blk "[$tap getName]_al${r}_${b}_n"]; $nn setSigType CLOCK
  foreach t [$inst getITerms] {
    set mt [$t getMTerm]; if {[$mt getSigType] ne "SIGNAL"} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $src } else { $t connect $nn }
  }
  lassign [$tap getLocation] x y
  $inst setLocation $x $y; $inst setPlacementStatus PLACED
  $a disconnect; $a connect $nn
}
# target = latest tap mean at r0 (fixed, so the target never chases the trunk-load drift); each tap keeps its own
# measured ps/cell (an inserted cell also unloads the trunk, so the first cell can even speed the tap up): clamped to
# 12..30 ps, default 20.  At most ceil(deficit/step) cells per round, never past the target.
# isolation (f790 v3d: the first delay cell in front of a BUFx24 tap took the tap's input load off the trunk and made
# the tap EARLIER, so alignment never converged): every tap first gets one identical isolation cell, so the trunk sees
# a uniform small load per tap and every later cell is pure delay.
if {![info exists ::env(OT_DTAP_ISO)] || $::env(OT_DTAP_ISO)} {
  set ta_iso 0
  foreach i [$ta_blk getInsts] { if {[regexp {^ot_dtap_[0-9]+$} [$i getName]]} { ta_add $i 0 iso; incr ta_iso } }
  detailed_placement
  puts "OT_DTAP_ALIGN iso: $ta_iso taps behind one [$ta_master getName] each"
}
set m [ta_measure]
puts [ta_line "OT_DTAP_ALIGN r0" $m]
set ta_tgt 0.0; dict for {n v} $m { set ta_tgt [expr {max($ta_tgt, [lindex $v 0])}] }
set ta_stp [dict create]
# safety: a tap never takes more than ceil(r0 deficit / 12 ps) + 1 cells in total, and a round whose measurement does
# not move (stale timing) stops the loop -- f790 v3c: a stale measure re-added the same deficit 4x -> 1.1 ns tree.
set ta_cap [dict create]; set ta_used [dict create]
dict for {n v} $m { dict set ta_cap $n [expr {int(ceil(($ta_tgt - [lindex $v 0]) / 12.0)) + 1}]; dict set ta_used $n 0 }
for {set r 1} {$r <= $ta_rounds} {incr r} {
  set added {}
  dict for {n v} $m {
    set d [expr {$ta_tgt - [lindex $v 0]}]
    if {$d <= $ta_tol} continue
    set st [expr {[dict exists $ta_stp $n] ? [dict get $ta_stp $n] : 20.0}]
    set nb [expr {int(floor($d / $st + 0.5))}]
    set nb [expr {min($nb, [dict get $ta_cap $n] - [dict get $ta_used $n])}]
    if {$nb < 1} continue
    dict incr ta_used $n $nb
    for {set b 0} {$b < $nb} {incr b} { ta_add [$ta_blk findInst $n] $r $b }
    lappend added $n $nb [lindex $v 0]
  }
  if {![llength $added]} break
  detailed_placement
  set m [ta_measure]
  set moved 0
  foreach {n nb a0} $added { if {abs([lindex [dict get $m $n] 0] - $a0) > 1.0} { set moved 1 } }
  if {!$moved} { puts "OT_DTAP_ALIGN WARN r$r: tap means did not move after [expr {[llength $added] / 3}] taps got delay cells (stale timing?) -- stop"; break }
  foreach {n nb a0} $added {
    set st [expr {([lindex [dict get $m $n] 0] - $a0) / double($nb)}]
    dict set ta_stp $n [expr {$st < 12.0 ? 12.0 : ($st > 30.0 ? 30.0 : $st)}]
  }
  puts "[ta_line "OT_DTAP_ALIGN r$r" $m] (target [format %.1f $ta_tgt])"
}
puts [ta_line "OT_DTAP_ALIGN final" $m]
}
set ta_next [expr {[info exists ::env(OT_DTAP_NEXT)] ? $::env(OT_DTAP_NEXT) : "/work/tap_balance.tcl"}]
if {$ta_next ne "" && [file exists $ta_next]} { source $ta_next }
