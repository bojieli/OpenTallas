# serdes_lanes.tcl (HARD-S81-SERDES-1 2026-11-13; PRE_GLOBAL_PLACE, sourced last in face_flops.tcl; opt-in: the kit has
# /work/serdes_lanes_cfg.tcl).  Hand floorplan of a shore serdes lot (form LANE of ot_pdie_serdes_col):
#   1. every LANE row register (ot_pl_pad chains u_lpin, u_txl, u_lrxi, u_lrxo) is placed FIRM on its per-bit lane, row k
#      of n at the fraction given below of the straight line between the lane's two ends, so no registered hop is longer
#      than the plan reach.  Wirelength-driven placement does not do this: a 2-pin register chain has the same HPWL
#      wherever its rows sit, so GPL leaves all rows at one end (serdes__t2 a27: u_txl r[0] -> q 2.2 mm).
#   2. placement blockages cover the lot outside the KP4 island and the pin strip, so GPL cannot spread 1.4 % of cells
#      over 3.5 mm2.  serdes_lanes_release.tcl (PRE_DETAIL_PLACE) removes them, so repair buffers, CTS and DPL are free.
# Rows are appended to ot_face_flops.txt (tag SLN): face_flops_release.tcl hands them to DPL as PLACED.
# cfg (um): sl_cfg dict  blocks {{x0 y0 x1 y1} ...}
#   chains {{name n kind ax ay bx by} ...}   kind: txl (b end = PMA TX pin x, y = by), rxi (a end = the RCK band flop / PMA
#   RX pin, b end = bx by), pt (both ends points; rows at (k+1)/(n+1)).  txl rows at (k+1)/n, rxi rows at k/n.
uplevel #0 {
set sl_blk [ord::get_db_block]; set sl_dbu [$sl_blk getDbUnitsPerMicron]
source /work/serdes_lanes_cfg.tcl
proc sl_u {v} { global sl_dbu; return [expr {int(round($v * $sl_dbu))}] }
proc sl_is_ff {i} { return [string match "*DFF*" [[$i getMaster] getName]] }
proc sl_is_buf {i} { return [regexp {^(BUF|INV|HB|CKINV)} [[$i getMaster] getName]] }
# forward from a net through buffers / inverters: list of {kind inst iterm} loads, kind ff (D pin) or macro
proc sl_fwd {net depth} {
  set out {}
  if {$net eq "NULL" || $depth > 8} { return $out }
  foreach s [$net getITerms] {
    if {![$s isInputSignal]} continue
    set i [$s getInst]
    if {[sl_is_ff $i]} { if {[[$s getMTerm] getName] eq "D"} { lappend out [list ff $i $s] } } \
    elseif {[sl_is_buf $i]} { foreach o [$i getITerms] { if {[$o isOutputSignal]} { lappend out {*}[sl_fwd [$o getNet] [expr {$depth + 1}]] } } } \
    elseif {[[$i getMaster] isBlock]} { lappend out [list macro $i $s] }
  }
  return $out
}
proc sl_fwd_of {f} {
  set out {}
  foreach o [$f getITerms] { if {[$o isOutputSignal]} { lappend out {*}[sl_fwd [$o getNet] 0] } }
  return $out
}
# legal rows: y -> {orient originX siteW}
set sl_rows {}
foreach r [$sl_blk getRows] {
  set o [$r getOrigin]; dict set sl_rows [lindex $o 1] [list [$r getOrient] [lindex $o 0] [[$r getSite] getWidth]]
}
set sl_ys [lsort -integer [dict keys $sl_rows]]
set sl_rh [expr {[lindex $sl_ys 1] - [lindex $sl_ys 0]}]; set sl_y0 [lindex $sl_ys 0]; set sl_ny [llength $sl_ys]
set sl_core [$sl_blk getCoreArea]
# macro keep-outs (2 um halo)
set sl_mac {}
foreach i [$sl_blk getInsts] {
  if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend sl_mac [list [expr {[$b xMin] - [sl_u 2]}] [expr {[$b yMin] - [sl_u 2]}] [expr {[$b xMax] + [sl_u 2]}] [expr {[$b yMax] + [sl_u 2]}]] }
}
set sl_occ {}
set sl_cp [sl_u 1.512]    ;# column pitch of the station grid: one flop (<= 1.4 um) per cell
proc sl_put {f x y} {
  global sl_occ sl_cp sl_rows sl_ys sl_rh sl_y0 sl_ny sl_mac sl_core
  set w [[$f getMaster] getWidth]
  set c0 [expr {int($x / $sl_cp)}]; set r0 [expr {int(($y - $sl_y0) / $sl_rh)}]
  for {set rad 0} {$rad < 400} {incr rad} {
    for {set dr [expr {-$rad}]} {$dr <= $rad} {incr dr} {
      foreach dc [lsort -unique [list [expr {$rad - abs($dr)}] [expr {abs($dr) - $rad}]]] {
        set c [expr {$c0 + $dc}]; set r [expr {$r0 + $dr}]
        if {$r < 0 || $r >= $sl_ny || $c < 0 || [dict exists $sl_occ "$c,$r"]} continue
        set cy [lindex $sl_ys $r]; lassign [dict get $sl_rows $cy] orient ox sw
        set cx [expr {$ox + int(round(double($c * $sl_cp - $ox) / $sw)) * $sw}]
        if {$cx < [$sl_core xMin] || $cx + $w > [$sl_core xMax]} continue
        set hit 0
        foreach m $sl_mac { lassign $m mx0 my0 mx1 my1; if {$cx < $mx1 && $cx + $w > $mx0 && $cy < $my1 && $cy + $sl_rh > $my0} { set hit 1; break } }
        if {$hit} continue
        dict set sl_occ "$c,$r" 1
        $f setOrient $orient; $f setLocation $cx $cy; $f setPlacementStatus FIRM
        return [list $cx $cy]
      }
    }
  }
  return ""
}
# ---- chains + blockages (in a proc: no globals of other hooks are touched)
proc sl_run {} {
global sl_blk sl_dbu sl_cfg
set sl_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
set sl_log {}
foreach ch [dict get $sl_cfg chains] {
  lassign $ch cn n kind ax ay bx by
  set ax [sl_u $ax]; set ay [sl_u $ay]; set bx [sl_u $bx]; set by [sl_u $by]
  catch {unset row}; array set row {}
  set bits {}
  set re [format {[./]%s[./]g_reg[./]r\\?\[(\d+)\\?\]\\?\[(\d+)\\?\]} $cn]
  foreach i [$sl_blk getInsts] {
    if {![sl_is_ff $i]} continue
    if {[regexp $re [$i getName] -> k b]} { set row($k,$b) $i; dict set bits $b 1 }
  }
  set nb [llength [dict keys $bits]]; set nplaced 0; set nmiss 0; set hmax 0; set nrow 0
  foreach b [lsort -integer [dict keys $bits]] {
    # row 0 by name; rows 1..n-1 by structure (the one flop each row drives): names of merged / last rows are not relied on
    if {![info exists row(0,$b)]} continue
    set fl [list $row(0,$b)]
    for {set k 1} {$k < $n} {incr k} {
      set nx ""; set pv [lindex $fl end]
      if {$pv ne ""} { foreach l [sl_fwd_of $pv] { if {[lindex $l 0] eq "ff"} { set nx [lindex $l 1]; break } } }
      lappend fl $nx
    }
    set last [lindex $fl end]
    set pax $ax; set pay $ay; set pbx $bx; set pby $by
    if {$kind eq "txl" && $last ne ""} {
      foreach l [sl_fwd_of $last] { if {[lindex $l 0] eq "macro"} { set bb [[lindex $l 2] getBBox]; set pbx [expr {([$bb xMin] + [$bb xMax]) / 2}]; break } }
    }
    if {$kind eq "rxi" && [lindex $fl 0] ne ""} {
      set f0 [lindex $fl 0]
      if {[$f0 getPlacementStatus] eq "FIRM"} { lassign [$f0 getLocation] pax pay } else {
        # no RCK band in this kit: the PMA pin x, y = ay
        foreach it [$f0 getITerms] { if {[$it isInputSignal] && [[$it getMTerm] getName] eq "D"} {
          set dn [$it getNet]; foreach s [$dn getITerms] { if {[$s isOutputSignal] && [[[$s getInst] getMaster] isBlock]} { set bb [$s getBBox]; set pax [expr {([$bb xMin] + [$bb xMax]) / 2}] } } } }
      }
    }
    set px $pax; set py $pay
    for {set k 0} {$k < $n} {incr k} {
      set f [lindex $fl $k]
      switch $kind { txl { set t [expr {double($k + 1) / $n}] } rxi { set t [expr {double($k) / $n}] } default { set t [expr {double($k + 1) / ($n + 1)}] } }
      set x [expr {int($pax + ($pbx - $pax) * $t)}]; set y [expr {int($pay + ($pby - $pay) * $t)}]
      if {$f eq ""} { incr nmiss; continue }
      incr nrow
      if {$kind eq "rxi" && $k == 0 && [$f getPlacementStatus] eq "FIRM"} { set xy [$f getLocation] } else {
        if {[$f getPlacementStatus] eq "FIRM"} { $f setPlacementStatus PLACED }
        set xy [sl_put $f $x $y]
        if {$xy eq ""} { incr nmiss; continue }
        puts $sl_fh "[$f getName]\tSLN\t[expr {[lindex $xy 0] / double($sl_dbu)}]\t[expr {[lindex $xy 1] / double($sl_dbu)}]\t$cn.$k"
        incr nplaced
      }
      set h [expr {abs([lindex $xy 0] - $px) + abs([lindex $xy 1] - $py)}]; if {$k > 0 || $kind ne "rxi"} { if {$h > $hmax} { set hmax $h } }
      lassign $xy px py
    }
    set h [expr {abs($pbx - $px) + abs($pby - $py)}]; if {$kind ne "txl" && $h > $hmax} { set hmax $h }
  }
  puts "OT_SERDES_LANES chain $cn kind $kind rows $n bits $nb: placed $nplaced FIRM, missing $nmiss, max planned hop [format %.1f [expr {$hmax / double($sl_dbu)}]] um"
  if {$nb == 0 || $nmiss > 0} { error "OT_SERDES_LANES chain $cn: $nb bits, $nmiss rows not found or not placed (RTL form / names changed?)" }
}
# ---- module anchors (cfg key anchors {{regexp x0 y0 x1 y1} ...}, optional): every not yet FIRM flop whose name matches
#      is placed FIRM on an even raster inside its box (dictionary order of the names), so each module's logic packs
#      around its own registers.  Why: the KP4 encoder / syndrome / RiBM cones are dense GF(2) matrices; left to one
#      shared island GPL interleaves the modules and every net is as long as the island (kitC2: 12 cells, 21 wire
#      buffers, 3.2 ns on u_syn.Sl -> u_bm.d).  The comb cells stay free and follow their registers.
if {[dict exists $sl_cfg anchors]} {
  foreach an [dict get $sl_cfg anchors] {
    lassign $an are x0 y0 x1 y1
    set x0 [sl_u $x0]; set y0 [sl_u $y0]; set x1 [sl_u $x1]; set y1 [sl_u $y1]
    set ffs {}
    foreach i [$sl_blk getInsts] {
      if {![sl_is_ff $i] || [$i getPlacementStatus] eq "FIRM"} continue
      if {[regexp $are [$i getName]]} { lappend ffs [list [$i getName] $i] }
    }
    set n [llength $ffs]
    if {$n == 0} { puts "OT_SERDES_LANES anchor $are: 0 flops (skipped)"; continue }
    set ffs [lsort -dictionary -index 0 $ffs]
    set cols [expr {int(ceil(sqrt(double($n) * ($x1 - $x0) / ($y1 - $y0))))}]; set rws [expr {int(ceil(double($n) / $cols))}]
    set k 0; set miss 0
    foreach e $ffs {
      set f [lindex $e 1]
      set x [expr {int($x0 + ($x1 - $x0) * (($k % $cols) + 0.5) / $cols)}]; set y [expr {int($y0 + ($y1 - $y0) * (($k / $cols) + 0.5) / $rws)}]
      set xy [sl_put $f $x $y]
      if {$xy eq ""} { incr miss } else { puts $sl_fh "[$f getName]	SLA	[expr {[lindex $xy 0] / double($sl_dbu)}]	[expr {[lindex $xy 1] / double($sl_dbu)}]	anchor" }
      incr k
    }
    puts "OT_SERDES_LANES anchor $are: $n flops FIRM on a $cols x $rws raster in ([expr {$x0 / double($sl_dbu)}] [expr {$y0 / double($sl_dbu)}] [expr {$x1 / double($sl_dbu)}] [expr {$y1 / double($sl_dbu)}]), unplaced $miss"
  }
}
close $sl_fh
# ---- blockages (removed again by serdes_lanes_release.tcl)
set sl_have {}
foreach k [$sl_blk getBlockages] { set bb [$k getBBox]; dict set sl_have "[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]" 1 }
set sl_nb 0; set sl_bf [open $::env(RESULTS_DIR)/ot_serdes_lane_blocks.txt w]
foreach r [dict get $sl_cfg blocks] {
  lassign $r x0 y0 x1 y1; set x0 [sl_u $x0]; set y0 [sl_u $y0]; set x1 [sl_u $x1]; set y1 [sl_u $y1]
  puts $sl_bf "$x0,$y0,$x1,$y1"
  if {![dict exists $sl_have "$x0,$y0,$x1,$y1"]} { odb::dbBlockage_create $sl_blk $x0 $y0 $x1 $y1; incr sl_nb }
}
close $sl_bf
puts "OT_SERDES_LANES blockages: $sl_nb created ([llength [dict get $sl_cfg blocks]] planned)"
}
sl_run
}
