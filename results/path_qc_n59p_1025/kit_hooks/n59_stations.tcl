# PATH-QC-N59-PROTO 2026-10-25 PRE_GLOBAL_PLACE hook (after face_flops.tcl, before macro_pin_flops.tcl): site the
# native59 QB_STN station registers (rtl/qwen_split/qfd_native59_qbank.sv, -DOT_N59_STN) on the pin -> SRAM-face path so
# every register hop is <= OT_N59_REACH_UM (405).  Placement only; FIRM until n59_stations_release.tcl (PRE_DETAIL_PLACE).
#   write path, per writer w (3 hops, the +1 station s2):  dd_i pin reg (E face) -> u_s1 -> u_s2 -> write-face replicas
#     (u_wc / u_wd, anchored at the write pins by macro_pin_flops).  Route = monotone L (horizontal at the pin y, then
#     vertical at the write-face x); s1 at L/3, s2 at 2L/3.
#   read controls, per bank w (2 hops, +0):  q_slot / q_slot_beat pin regs (S face) -> u_sr -> u_rm (read pins, MPF).
#     Route = horizontal at the pin y to the read-face x, then vertical; u_sr at L/2.
# A site inside a macro (+ halo + gap + group size) moves along y to the nearest free position (row channel / strip).
set n59s_blk [ord::get_db_block]
set n59s_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n59s_halo 5.4; set n59s_gap 0.54; set n59s_off 3.0
set n59s_core [$n59s_blk getCoreArea]
set n59s_cx0 [expr {double([$n59s_core xMin]) / $n59s_dbu}]; set n59s_cx1 [expr {double([$n59s_core xMax]) / $n59s_dbu}]
set n59s_cy0 [expr {double([$n59s_core yMin]) / $n59s_dbu}]; set n59s_cy1 [expr {double([$n59s_core yMax]) / $n59s_dbu}]
set n59s_die_w [expr {double([[$n59s_blk getDieArea] xMax]) / $n59s_dbu}]
# macros
set n59s_mac [dict create]; set n59s_boxes {}
foreach i [$n59s_blk getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set b [$i getBBox]
  set bx [list [expr {double([$b xMin])/$n59s_dbu}] [expr {double([$b yMin])/$n59s_dbu}] [expr {double([$b xMax])/$n59s_dbu}] [expr {double([$b yMax])/$n59s_dbu}]]
  lappend n59s_boxes $bx
  if {[regexp {g_writer\\?\[([0-9]+)\\?\]} [$i getName] -> w]} { dict set n59s_mac $w $bx }
}
proc n59s_free {x y boxes m} {
  foreach b $boxes { lassign $b x0 y0 x1 y1
    if {$x > $x0 - $m && $x < $x1 + $m && $y > $y0 - $m && $y < $y1 + $m} { return 0 } }
  return 1
}
proc n59s_legal {x y boxes m cy0 cy1} {
  if {[n59s_free $x $y $boxes $m]} { return [list $x $y] }
  for {set d 1.0} {$d < 200.0} {set d [expr {$d + 1.0}]} {
    foreach yy [list [expr {$y + $d}] [expr {$y - $d}]] {
      if {$yy > $cy0 + $m && $yy < $cy1 - $m && [n59s_free $x $yy $boxes $m]} { return [list $x $yy] }
    }
  }
  return [list $x $y]
}
# point at distance s along the monotone L (x0,y0) -> (x1,y0) -> (x1,y1)
proc n59s_along {x0 y0 x1 y1 s} {
  set lx [expr {abs($x1 - $x0)}]
  if {$s <= $lx} { return [list [expr {$x0 + ($x1 > $x0 ? $s : -$s)}] $y0] }
  set r [expr {$s - $lx}]
  return [list $x1 [expr {$y0 + ($y1 > $y0 ? $r : -$r)}]]
}
proc n59s_pins {blk dbu re} {
  set sx 0.0; set sy 0.0; set n 0
  foreach bt [$blk getBTerms] {
    if {![regexp $re [$bt getName]]} continue
    set bb [$bt getBBox]
    set sx [expr {$sx + ([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}]; set sy [expr {$sy + ([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]; incr n
  }
  if {!$n} { error "n59_stations: no pins match $re" }
  return [list [expr {$sx / $n}] [expr {$sy / $n}]]
}
# station flops by group
set n59s_grp [dict create]
foreach i [$n59s_blk getInsts] {
  set nm [$i getName]
  if {[regexp {g_wif\.g_w\\?\[([0-9]+)\\?\]\.g_stn[./]u_s([12])[./]} $nm -> w s]} { dict lappend n59s_grp "w$w.s$s" $i
  } elseif {[regexp {g_rstn\.g_w\\?\[([0-9]+)\\?\]\.?[./]?u_sr[./]} $nm -> w]} { dict lappend n59s_grp "r$w.sr" $i }
}
if {[dict size $n59s_grp] != 24} { error "n59_stations: expected 24 station groups (8 x s1/s2 + 8 sr), found [dict size $n59s_grp]: [dict keys $n59s_grp]" }
set n59s_list {}; set n59s_rep {}
proc n59s_place {grp x y} {
  upvar 1 n59s_dbu dbu n59s_list lst n59s_cx0 cx0 n59s_cx1 cx1 n59s_cy0 cy0 n59s_cy1 cy1
  set k 0; set ncol 6
  foreach i $grp {
    set w [expr {double([[$i getMaster] getWidth]) / $dbu}]; set h [expr {double([[$i getMaster] getHeight]) / $dbu}]
    set xx [expr {$x + (($k % $ncol) - $ncol / 2) * ($w + 0.216)}]
    set yy [expr {$y + (($k / $ncol) - 4) * $h}]
    set xx [expr {min(max($xx, $cx0), $cx1 - $w)}]
    set yy [expr {$cy0 + round((min(max($yy, $cy0), $cy1 - $h) - $cy0) / $h) * $h}]
    $i setLocation [expr {round($xx * $dbu)}] [expr {round($yy * $dbu)}]
    $i setPlacementStatus FIRM
    lappend lst [$i getName]; incr k
  }
}
set n59s_m [expr {$n59s_halo + $n59s_gap + 6.0}]
for {set w 0} {$w < 8} {incr w} {
  lassign [dict get $n59s_mac $w] mx0 my0 mx1 my1
  set yc [expr {($my0 + $my1) / 2.0}]
  set left [expr {$mx0 < $n59s_die_w / 2.0}]
  # write face: W edge of the left column (MY), E edge of the right column (R0); read face the other edge
  set wx [expr {$left ? $mx0 - $n59s_halo - $n59s_off : $mx1 + $n59s_halo + $n59s_off}]
  set rx [expr {$left ? $mx1 + $n59s_halo + $n59s_off : $mx0 - $n59s_halo - $n59s_off}]
  set lo [expr {89 + 32 * $w}]; set hi [expr {$lo + 31}]
  set bits {}; for {set b $lo} {$b <= $hi} {incr b} { lappend bits $b }
  lassign [n59s_pins $n59s_blk $n59s_dbu [format {^dd_i\\?\[(%s)\\?\]$} [join $bits |]]] px py
  set L [expr {abs($wx - $px) + abs($yc - $py)}]
  lassign [n59s_legal {*}[n59s_along $px $py $wx $yc [expr {$L / 3.0}]] $n59s_boxes $n59s_m $n59s_cy0 $n59s_cy1] s1x s1y
  lassign [n59s_legal {*}[n59s_along $px $py $wx $yc [expr {2.0 * $L / 3.0}]] $n59s_boxes $n59s_m $n59s_cy0 $n59s_cy1] s2x s2y
  n59s_place [dict get $n59s_grp "w$w.s1"] $s1x $s1y
  n59s_place [dict get $n59s_grp "w$w.s2"] $s2x $s2y
  set h1 [expr {abs($s1x - $px) + abs($s1y - $py)}]; set h2 [expr {abs($s2x - $s1x) + abs($s2y - $s1y)}]; set h3 [expr {abs($wx - $s2x) + abs($yc - $s2y)}]
  lappend n59s_rep [format "w%d write: pin (%.1f,%.1f) s1 (%.1f,%.1f) s2 (%.1f,%.1f) face (%.1f,%.1f) L %.1f hops %.1f %.1f %.1f" $w $px $py $s1x $s1y $s2x $s2y $wx $yc $L $h1 $h2 $h3]
  lassign [n59s_pins $n59s_blk $n59s_dbu {^q_slot(_beat)?\\?\[[0-9]+\\?\]$}] qx qy
  set Lr [expr {abs($rx - $qx) + abs($yc - $qy)}]
  lassign [n59s_legal {*}[n59s_along $qx $qy $rx $yc [expr {$Lr / 2.0}]] $n59s_boxes $n59s_m $n59s_cy0 $n59s_cy1] srx sry
  n59s_place [dict get $n59s_grp "r$w.sr"] $srx $sry
  lappend n59s_rep [format "r%d read : pin (%.1f,%.1f) sr (%.1f,%.1f) face (%.1f,%.1f) L %.1f hops %.1f %.1f" $w $qx $qy $srx $sry $rx $yc $Lr \
    [expr {abs($srx - $qx) + abs($sry - $qy)}] [expr {abs($rx - $srx) + abs($yc - $sry)}]]
}
set n59s_as /src/physical/common_flow/anchor_row_packing.tcl
if {![file exists $n59s_as]} { set n59s_as /work/cf/anchor_row_packing.tcl }
source $n59s_as
ot_anchor_pack::repair $n59s_blk $n59s_list
set fh [open $::env(RESULTS_DIR)/ot_n59_stations.txt w]
foreach l $n59s_rep { puts $fh $l; puts "OT_N59_STN $l" }
foreach n $n59s_list { puts $fh "inst $n" }
close $fh
puts "OT_N59_STN placed [llength $n59s_list] station flops in [dict size $n59s_grp] groups (FIRM until PRE_DETAIL_PLACE)"
