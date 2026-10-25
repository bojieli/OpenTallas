# PATH-KV-ASTK4 10-25 (PRE_CTS, after max_fanout.tcl): kv3_astk regional clock taps, successor of astk_zone_taps.tcl.
# Why (PATH-KV-ASTK3 14:48, CTS1 STRUCTURAL FAIL): ONE 'rest' tap (4042 sinks at the ctl band centroid 108,49) clocked
# the ctl interior AND every boundary pin register of the N/E/S faces; the N-face pin regs hung on ~125 um branches
# (N mean 306 / max 326 ps vs bound 250; group spread 53 > 20).  CLOCK-RESET rule LC1 (COORD APPROVED 14:58): the pin
# registers of a face are their own tap groups (bounded sinks / span along the face, never a whole band or interior tree).
# Groups here (one tap buffer OT_LANE_TAP_CELL at each group's centroid, one new CLOCK net per tap):
#   * pinreg_<F><i>: boundary pin registers (postcts_gate / pinreg_pad set: register endpoints in the fanout of the data
#     inputs + startpoints in the fanin of the outputs), by nearest face F (N/E/S/W), cut along the face into equal-count
#     rows of <= OT_PR_TAP_MAX_SINKS (500) sinks and <= OT_PR_TAP_MAX_SPAN_UM (150) um;
#   * the 4 dataflow zones (capture 1 of OT_LANE_RE: u_u_strip_u_strip_g_zn_<k>_u_zn), interior only;
#   * ctl: everything else (ctl interior, strap landing, fault) at its own centroid.
# CTS (-sink_clustering_enable -balance_levels) builds one tree per tap and the top tree from the port to the tap
# inputs with matched levels, so every tap sits on an equal-level branch from the core root.
# Writes $RESULTS_DIR/ot_lane_taps.json {tap: {group, sinks, x, y}}.
uplevel #0 {
set t4_re [expr {[info exists ::env(OT_LANE_RE)] ? $::env(OT_LANE_RE) : {^(u_u_strip_u_strip_g_zn_[0-9]_u_zn)[./]}}]
set t4_cell [expr {[info exists ::env(OT_LANE_TAP_CELL)] ? $::env(OT_LANE_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set t4_maxn [expr {[info exists ::env(OT_PR_TAP_MAX_SINKS)] ? $::env(OT_PR_TAP_MAX_SINKS) : 500}]
set t4_maxs [expr {[info exists ::env(OT_PR_TAP_MAX_SPAN_UM)] ? $::env(OT_PR_TAP_MAX_SPAN_UM) : 150.0}]
set t4_blk [ord::get_db_block]
set t4_u [[ord::get_db_tech] getDbUnitsPerMicron]
set t4_master [[ord::get_db] findMaster $t4_cell]
if {$t4_master eq "NULL" || $t4_master eq ""} { error "OT_TAPS4: no master $t4_cell" }
set t4_in ""; set t4_out ""
foreach mt [$t4_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set t4_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set t4_out [$mt getName] }
}
# ---- boundary pin registers (the postcts_gate.tcl / pinreg_pad.tcl set) -----------------------------------------------
set t4_pr [dict create]
set t4_din [all_inputs -no_clocks]
if {[llength $t4_din]} {
  foreach p [get_fanout -from $t4_din -flat -endpoints_only -trace_arcs all] {
    if {![catch {set it [sta::sta_to_db_pin $p]}] && $it ne "NULL" && $it ne ""} { dict set t4_pr [[$it getInst] getName] 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    if {![catch {set it [sta::sta_to_db_pin $p]}] && $it ne "NULL" && $it ne ""} { dict set t4_pr [[$it getInst] getName] 1 }
  }
}
set t4_die [$t4_blk getDieArea]
set t4_x0 [$t4_die xMin]; set t4_y0 [$t4_die yMin]; set t4_x1 [$t4_die xMax]; set t4_y1 [$t4_die yMax]
proc t4_face {x y} {
  global t4_x0 t4_y0 t4_x1 t4_y1
  set d [list [list W [expr {$x - $t4_x0}]] [list E [expr {$t4_x1 - $x}]] [list S [expr {$y - $t4_y0}]] [list N [expr {$t4_y1 - $y}]]]
  return [lindex [lsort -real -index 1 $d] 0 0]
}
# the clock root net(s): nets of the SDC clock source ports
set t4_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$t4_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend t4_roots [$bt getNet] }
  }
}
set t4_js {}
set j 0
foreach root [lsort -unique $t4_roots] {
  set groups [dict create]
  set faces [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    set nm [$inst getName]
    if {[dict exists $t4_pr $nm]} {
      lassign [$inst getLocation] x y
      dict lappend faces [t4_face $x $y] $it
      continue
    }
    set k [expr {[regexp $t4_re $nm -> kk] ? $kk : "ctl"}]
    dict lappend groups $k $it
  }
  # face rows: equal-count cuts along the face, <= t4_maxn sinks and <= t4_maxs um each
  dict for {f its} $faces {
    set ax [expr {$f in {N S} ? 0 : 1}]
    set rec {}
    foreach it $its { lappend rec [list [lindex [[$it getInst] getLocation] $ax] $it] }
    set rec [lsort -integer -index 0 $rec]
    set n [llength $rec]
    set span [expr {double([lindex $rec end 0] - [lindex $rec 0 0]) / $t4_u}]
    set k [expr {max(int(ceil(double($n) / $t4_maxn)), int(ceil($span / $t4_maxs)), 1)}]
    for {set c 0} {$c < $k} {incr c} {
      set a [expr {($c * $n) / $k}]; set b [expr {(($c + 1) * $n) / $k - 1}]
      set row {}
      foreach r [lrange $rec $a $b] { lappend row [lindex $r 1] }
      if {[llength $row]} { dict set groups "pinreg_$f$c" $row }
    }
    puts [format "OT_TAPS4 face %s: %d pin regs, span %.1f um -> %d row tap(s)" $f $n $span $k]
  }
  if {[dict size $groups] < 2} { puts "OT_TAPS4 [$root getName]: [dict size $groups] group(s), no taps"; continue }
  dict for {k its} $groups {
    set sx 0.0; set sy 0.0
    foreach it $its { lassign [[$it getInst] getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}] }
    set cx [expr {round($sx / [llength $its])}]; set cy [expr {round($sy / [llength $its])}]
    set nm "ot_lane_tap_$j"
    set b [odb::dbInst_create $t4_blk $t4_master $nm]
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    set net [odb::dbNet_create $t4_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $t4_in] connect $root
    [$b findITerm $t4_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    puts [format "OT_TAPS4 %s %s sinks %d at %.1f %.1f" $nm $k [llength $its] [expr {double($cx) / $t4_u}] [expr {double($cy) / $t4_u}]]
    lappend t4_js "\"$nm\": {\"group\": \"[string map {\\ {}} $k]\", \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($cx) / $t4_u}]], \"y\": [format %.2f [expr {double($cy) / $t4_u}]]}"
    incr j
  }
  puts "OT_TAPS4 [$root getName]: $j taps ([dict size $t4_pr] pin regs)"
}
if {![dict size $t4_pr]} { error "OT_TAPS4: no boundary pin registers found (STA not loaded?)" }
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_lane_taps.json w]; puts $fh "{[join $t4_js {, }]}"; close $fh
}
}
