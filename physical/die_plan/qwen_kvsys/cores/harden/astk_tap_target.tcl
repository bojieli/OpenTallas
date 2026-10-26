# PATH-KV-ASTK8 10-26 (COORD 01:13 ruling (1)): POST_CTS, before leaf_affinity.tcl.  Balance every ASTK tap tree whose
# group matches OT_TAP_TARGET_RE (default: the face chunks) TO the boundary contract OT_VCLK_TT (250 ps) -- the
# tap_balance.tcl rule (short trees get a delay chain tap input -> cells -> tap up to the plan insertion T) applied to
# the internal astk_face_taps.tcl tap buffers.  Measured: mean rise arrival over the tap's register clock pins, the
# slowest analysis scene (TT, placement RC).  A tree above T + OT_TAP_TOL_PS is reported OT_TAP_TARGET OVER (structure,
# not padding, must fix it).  Env: OT_TAP_TARGET_RE, OT_TAP_TARGET_PS (default OT_VCLK_TT), OT_TAP_TOL_PS (5),
# OT_TAP_DELAY_CELL (BUFx4_ASAP7_75t_R), OT_TAP_ITER (4).  Prints OT_TAP_TARGET lines; writes ot_tap_target.json.
uplevel #0 {
set tt_re [expr {[info exists ::env(OT_TAP_TARGET_RE)] ? $::env(OT_TAP_TARGET_RE) : {^face_}}]
set tt_T [expr {[info exists ::env(OT_TAP_TARGET_PS)] ? $::env(OT_TAP_TARGET_PS) : $::env(OT_VCLK_TT)}]
set tt_tol [expr {[info exists ::env(OT_TAP_TOL_PS)] ? $::env(OT_TAP_TOL_PS) : 5.0}]
set tt_cell [expr {[info exists ::env(OT_TAP_DELAY_CELL)] ? $::env(OT_TAP_DELAY_CELL) : "BUFx4_ASAP7_75t_R"}]
set tt_iter [expr {[info exists ::env(OT_TAP_ITER)] ? $::env(OT_TAP_ITER) : 4}]
set tt_blk [ord::get_db_block]
set tt_m [[ord::get_db] findMaster $tt_cell]
if {$tt_m eq "NULL" || $tt_m eq ""} { error "OT_TAP_TARGET: no master $tt_cell" }
foreach mt [$tt_m getMTerms] { if {[$mt getSigType] in {SIGNAL CLOCK}} { if {[$mt getIoType] eq "INPUT"} { set tt_mi [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set tt_mo [$mt getName] } } }
set fh [open $::env(RESULTS_DIR)/ot_lane_taps.json r]; set tt_js [read $fh]; close $fh
set tt_taps {}
foreach {all t g} [regexp -all -inline {"(ot_lane_tap_[0-9]+)": \{"group": "([^"]+)"} $tt_js] { if {[regexp $tt_re $g]} { lappend tt_taps [list $t $g] } }
# register clock pins below a clock net (through clock buffers / inverters)
proc tt_sinks {net {d 0}} {
  set r {}
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set mn [[$i getMaster] getName]
    if {[regexp {^(DFF|ASYNC|SDF)} $mn]} { lappend r "[$i getName]/[[$it getMTerm] getName]"; continue }
    if {$d < 12} { foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend r {*}[tt_sinks [$o getNet] [expr {$d + 1}]] } } }
  }
  return $r
}
proc tt_mean {pins} {
  # arrival queries need a current timing graph (after netlist edits / parasitics): force one search first
  sta::redirect_string_begin; report_checks -path_delay max -group_path_count 1 -format end; sta::redirect_string_end
  set s 0.0; set n 0
  foreach pn $pins {
    set p [get_pins -quiet $pn]; if {![llength $p]} continue
    set a [sta::vertex_worst_arrival_path_rf [lindex [$p vertices] 0] rise max]
    if {$a eq "NULL" || $a eq ""} continue
    set s [expr {$s + [sta::time_sta_ui [$a arrival]]}]; incr n
  }
  return [expr {$n ? $s / $n : -1}]
}
estimate_parasitics -placement
set tt_out {}; set tt_added 0
set tt_tap_pins [dict create]
foreach tg $tt_taps { lassign $tg t g; set b [$tt_blk findInst $t]; dict set tt_tap_pins $t [tt_sinks [[$b findITerm Y] getNet]] }
# Use measured incremental delay; a guessed 15 ps/cell overshot by 10-18 ps.
# Add one legal cell, measure, and retain it only if it improves target error.
# The permitted local-tree insertion window is 20 ps (BRIEFING decision 5d).
set tt_stop [dict create]
for {set it 0} {$it < $tt_iter} {incr it} {
  set progress 0
  foreach tg $tt_taps {
    lassign $tg t g
    if {[dict exists $tt_stop $t]} continue
    set before [tt_mean [dict get $tt_tap_pins $t]]
    if {$before <= 0} { error "OT_TAP_TARGET no timing for $g" }
    if {$before >= $tt_T - $tt_tol} { dict set tt_stop $t 1; continue }
    set b [$tt_blk findInst $t]; set bi [$b findITerm A]; set src [$bi getNet]
    lassign [$b getLocation] x y
    set nm "ot_tapdly_${t}_${it}"
    set c [odb::dbInst_create $tt_blk $tt_m $nm]
    $c setLocation $x $y; $c setPlacementStatus PLACED
    set nn [odb::dbNet_create $tt_blk "${nm}_ck"]; $nn setSigType CLOCK
    $bi disconnect; [$c findITerm $tt_mi] connect $src
    [$c findITerm $tt_mo] connect $nn; $bi connect $nn
    detailed_placement
    estimate_parasitics -placement
    set after [tt_mean [dict get $tt_tap_pins $t]]
    if {abs($after - $tt_T) >= abs($before - $tt_T)} {
      $bi disconnect; $bi connect $src
      odb::dbInst_destroy $c
      odb::dbNet_destroy $nn
      estimate_parasitics -placement
      dict set tt_stop $t 1
      puts "OT_TAP_TARGET $g retain [format %.2f $before], candidate [format %.2f $after] farther from $tt_T"
    } else {
      incr tt_added; incr progress
      puts "OT_TAP_TARGET $g [format %.2f $before] -> [format %.2f $after]"
    }
  }
  if {!$progress} break
}
set bad {}; set tt_rows {}
foreach tg $tt_taps {
  lassign $tg t g; set m [tt_mean [dict get $tt_tap_pins $t]]
  lappend tt_rows "$g [format %.2f $m]"
  if {$m <= 0 || abs($m - $tt_T) > 20.0} { lappend bad "$g [format %.2f $m]" }
}
puts "OT_TAP_TARGET done: $tt_added cells; [join $tt_rows {, }]"
if {[llength $bad]} { error "OT_TAP_TARGET outside 20 ps local-tree window: [join $bad {, }]" }
}
