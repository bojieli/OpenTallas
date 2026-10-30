# KV-KITS-V 2026-10-29 (kit-local, form of main physical/die_plan/qwen_kvsys/cores/harden/astk_zone_taps.tcl):
# qkd_kvs_pc has ONE interior clock entry (ck[0] at the core centre, 12.8a) and a 397x363 outline, so its far-corner
# register sinks sit up to ~370 um from the only entry (12.8b reach <= ~200).  PRE_DETAIL_PLACE (after GPL): every
# register / macro clock pin on the root clock net is grouped by core quadrant; each quadrant gets ONE clock buffer
# (OT_PCQ_TAP_CELL) at the plan-computed quadrant centre (snapped to a free legal site, status FIRM), driving a new
# CLOCK net with exactly that quadrant's sinks.  TritonCTS then builds one tree per tap net plus the top tree from the
# port to the 4 taps (CTS_ARGS -balance_levels).  Worst sink -> tap Manhattan ~= quadrant half-width + half-height.
# Writes $RESULTS_DIR/ot_pc_quad_taps.json.
uplevel #0 {
set pq_cell [expr {[info exists ::env(OT_PCQ_TAP_CELL)] ? $::env(OT_PCQ_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set pq_blk [ord::get_db_block]
set pq_u [[ord::get_db_tech] getDbUnitsPerMicron]
set pq_master [[ord::get_db] findMaster $pq_cell]
if {$pq_master eq "NULL" || $pq_master eq ""} { error "OT_PCQ_TAPS: no master $pq_cell" }
set pq_in ""; set pq_out ""
foreach mt [$pq_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set pq_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set pq_out [$mt getName] }
}
set pq_core [$pq_blk getCoreArea]
set pq_x0 [$pq_core xMin]; set pq_y0 [$pq_core yMin]; set pq_x1 [$pq_core xMax]; set pq_y1 [$pq_core yMax]
set pq_cx [expr {($pq_x0 + $pq_x1) / 2}]; set pq_cy [expr {($pq_y0 + $pq_y1) / 2}]
set pq_w [$pq_master getWidth]; set pq_h [$pq_master getHeight]
# fixed obstacles (tapcells, endcaps, FIRM face flops, macros) by row y
set pq_fixed {}
foreach i [$pq_blk getInsts] {
  if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
  set b [$i getBBox]
  lappend pq_fixed [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
proc pq_free {x y w h} {
  global pq_fixed
  foreach b $pq_fixed {
    lassign $b a c e f
    if {$a < $x + $w && $e > $x && $c < $y + $h && $f > $y} { return 0 }
  }
  return 1
}
proc pq_site {tx ty} {
  global pq_blk pq_w pq_h
  set best {}
  foreach r [$pq_blk getRows] {
    lassign [$r getOrigin] ox oy
    set bb [$r getBBox]
    if {$oy > $ty + 4*$pq_h || $oy < $ty - 4*$pq_h} continue
    set sw [[$r getSite] getWidth]
    set x [expr {$ox + round(double($tx - $ox) / $sw) * $sw}]
    for {set k 0} {$k < 400} {incr k} {
      foreach s [list $k [expr {-$k}]] {
        set xx [expr {$x + $s * $sw}]
        if {$xx < [$bb xMin] || $xx + $pq_w > [$bb xMax]} continue
        if {[pq_free $xx $oy $pq_w $pq_h]} {
          set d [expr {abs($xx - $tx) + abs($oy - $ty)}]
          if {$best eq "" || $d < [lindex $best 0]} { set best [list $d $xx $oy [$r getOrient]] }
          break
        }
      }
      if {$best ne "" && [lindex $best 0] <= abs($oy - $ty) + $k * $sw} break
    }
  }
  return $best
}
set pq_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$pq_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend pq_roots [$bt getNet] }
  }
}
set pq_js {}
set j 0
foreach root [lsort -unique $pq_roots] {
  set groups [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    lassign [$inst getLocation] x y
    set q [expr {($x >= $pq_cx ? 1 : 0) + ($y >= $pq_cy ? 2 : 0)}]
    dict lappend groups $q $it
  }
  if {[dict size $groups] < 2} { puts "OT_PCQ_TAPS [$root getName]: [dict size $groups] group(s), no taps"; continue }
  dict for {q its} $groups {
    set tx [expr {($q & 1) ? ($pq_cx + $pq_x1) / 2 : ($pq_x0 + $pq_cx) / 2}]
    set ty [expr {($q & 2) ? ($pq_cy + $pq_y1) / 2 : ($pq_y0 + $pq_cy) / 2}]
    set s [pq_site $tx $ty]
    if {$s eq ""} { error "OT_PCQ_TAPS: no free site near quadrant $q centre" }
    lassign $s d sx sy so
    set nm "ot_pcq_tap_$j"
    set b [odb::dbInst_create $pq_blk $pq_master $nm]
    $b setOrient $so
    $b setLocation $sx $sy
    $b setPlacementStatus FIRM
    set net [odb::dbNet_create $pq_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $pq_in] connect $root
    [$b findITerm $pq_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    puts [format "OT_PCQ_TAPS %s q%d sinks %d at %.2f %.2f (target %.2f %.2f)" $nm $q [llength $its] \
      [expr {double($sx) / $pq_u}] [expr {double($sy) / $pq_u}] [expr {double($tx) / $pq_u}] [expr {double($ty) / $pq_u}]]
    lappend pq_js "\"$nm\": {\"quadrant\": $q, \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($sx) / $pq_u}]], \"y\": [format %.2f [expr {double($sy) / $pq_u}]]}"
    incr j
  }
}
set fh [open $::env(RESULTS_DIR)/ot_pc_quad_taps.json w]
puts $fh "{[join $pq_js {, }]}"
close $fh
}
