# vm_cp_re PRE_GLOBAL_PLACE hook (FACE2/FACE3 2026-10-13): placement BY CONSTRUCTION, no RePlAce.
# The tile is a sparse fork (tap[2063] W -> se S + ne N from cx4 on, one merged flop per bit): RePlAce diverged
# (GPL-0305) in cx1 (free flops) and cx2 (flops FIRM at pins); cx3 (se + ne on E) congested at the se|ne seam.
# Here global_placement is replaced by a river plan (cx4: every fork flop takes the corner rule below = its S/N pin
# column x, its tap pin y, so tap run, flop and both output pins share one M4 track and one M3 track):
#   * (cx1-cx3 geometry only) a flop fed from a W/E pin and driving W/E pins sits on its OWN vertical column x_i (rank of
#     its input pin y, spread linearly over the core width) at its input pin y;
#   * a flop fed from an S/N pin and driving a W/E pin sits at the corner (x of the input pin, y of the output pin);
#   * every other cell (port buffers, inverters) sits at the port it touches, else at its flop.
# Cells are packed per row left to right (1 site gap) and left PLACED: detailed placement only legalises.
proc ot_fp_ports { inst dir } {
  # ports reached from inst going backward (dir=in) / forward (dir=out) through <= 6 combinational cells
  set seen [dict create]; set front [list $inst]; set out {}
  for { set h 0 } { $h < 6 && [llength $front] } { incr h } {
    set nxt {}
    foreach i $front {
      foreach it [$i getITerms] {
        if { ![$it isInputSignal] && ![$it isOutputSignal] } { continue }
        if { ($dir eq "in") != [$it isInputSignal] } { continue }
        set n [$it getNet]; if { $n eq "NULL" || [$n getSigType] ne "SIGNAL" } { continue }
        if { [$n getName] eq $::env(OT_FP_CLK) || [llength [$n getITerms]] > 64 } { continue }
        foreach b [$n getBTerms] { lappend out $b }
        foreach jt [$n getITerms] {
          set j [$jt getInst]
          if { $j eq $i || [dict exists $seen $j] || [[$j getMaster] isSequential] } { continue }
          if { ($dir eq "in") == [$jt isInputSignal] } { continue }
          dict set seen $j 1; lappend nxt $j
        }
      }
    }
    set front $nxt
  }
  return $out
}
proc ot_fp_xy { b } { set r [$b getBBox]; return [list [expr {([$r xMin]+[$r xMax])/2}] [expr {([$r yMin]+[$r yMax])/2}]] }
proc ot_fp_face { b core } {
  lassign [ot_fp_xy $b] x y
  set d [list [expr {$x-[$core xMin]}] [expr {[$core xMax]-$x}] [expr {$y-[$core yMin]}] [expr {[$core yMax]-$y}]]
  set m [tcl::mathfunc::min {*}$d]
  return [expr {[lindex $d 0]==$m || [lindex $d 1]==$m ? "H" : "V"}]
}
proc ot_re_fixed_place { args } {
  set block [ord::get_db_block]; set core [$block getCoreArea]
  set rows [lsort -command {apply {{a b} {expr {[lindex [$a getOrigin] 1]-[lindex [$b getOrigin] 1]}}}} [$block getRows]]
  set r0 [lindex $rows 0]; set sw [[$r0 getSite] getWidth]; set rh [[$r0 getSite] getHeight]
  set x0 [lindex [$r0 getOrigin] 0]; set y0 [lindex [$r0 getOrigin] 1]; set nr [llength $rows]
  set xmax [expr {$x0 + [$r0 getSiteCount]*$sw}]
  set tgt [dict create]; set col {}; set rest {}
  foreach i [$block getInsts] {
    if { [$i isPlaced] || [$i isFixed] } { continue }
    if { ![[$i getMaster] isSequential] } { lappend rest $i; continue }
    set ins [ot_fp_ports $i in]; set outs [ot_fp_ports $i out]
    if { ![llength $ins] || ![llength $outs] } { lappend rest $i; continue }
    set pi [lindex $ins 0]; set po [lindex $outs 0]
    if { [ot_fp_face $pi $core] eq "H" && [ot_fp_face $po $core] eq "H" } {
      lappend col [list [lindex [ot_fp_xy $pi] 1] $i]
    } elseif { [ot_fp_face $pi $core] eq "V" } {
      dict set tgt $i [list [lindex [ot_fp_xy $pi] 0] [lindex [ot_fp_xy $po] 1]]
    } else {
      dict set tgt $i [list [lindex [ot_fp_xy $po] 0] [lindex [ot_fp_xy $pi] 1]]
    }
  }
  set col [lsort -integer -index 0 $col]; set n [llength $col]
  set m [expr {2000 * [$block getDbUnitsPerMicron] / 1000}]
  set k 0
  foreach c $col {
    set x [expr {$x0 + $m + ($xmax - $x0 - 2*$m - 30*$sw) * $k / [expr {max(1,$n-1)}]}]
    dict set tgt [lindex $c 1] [list $x [lindex $c 0]]; incr k
  }
  set nflop [dict size $tgt]; set atport 0; set atflop 0
  foreach i $rest {
    set p {}
    foreach it [$i getITerms] {
      set nn [$it getNet]; if { $nn eq "NULL" || [$nn getSigType] ne "SIGNAL" } { continue }
      set bs [$nn getBTerms]; if { [llength $bs] } { set p [ot_fp_xy [lindex $bs 0]]; incr atport; break }
    }
    if { $p eq "" } {
      foreach it [$i getITerms] {
        set nn [$it getNet]; if { $nn eq "NULL" || [$nn getSigType] ne "SIGNAL" || [llength [$nn getITerms]] > 64 } { continue }
        foreach jt [$nn getITerms] { set j [$jt getInst]; if { [dict exists $tgt $j] } { set p [dict get $tgt $j]; break } }
        if { $p ne "" } { incr atflop; break }
      }
    }
    if { $p eq "" } { set p [list [expr {($x0+$xmax)/2}] [expr {$y0 + $nr*$rh/2}]] }
    dict set tgt $i $p
  }
  # per-row pack
  set byrow [dict create]
  dict for { i p } $tgt {
    set r [expr {max(0, min($nr-1, ([lindex $p 1]-$y0)/$rh))}]
    dict lappend byrow $r [list [lindex $p 0] $i]
  }
  dict for { r lst } $byrow {
    set row [lindex $rows $r]; set y [lindex [$row getOrigin] 1]; set o [$row getOrient]
    set lst [lsort -integer -index 0 $lst]
    set tot 0; foreach e $lst { incr tot [expr {[[[lindex $e 1] getMaster] getWidth] + $sw}] }
    set cur $x0
    foreach e $lst {
      set i [lindex $e 1]; set w [[$i getMaster] getWidth]
      set x [expr {$x0 + (([lindex $e 0]-$x0)/$sw)*$sw}]
      set x [expr {max($cur, min($x, $xmax - $tot))}]
      $i setOrient $o; $i setLocation $x $y; $i setPlacementStatus PLACED
      set cur [expr {$x + $w + $sw}]; set tot [expr {$tot - $w - $sw}]
    }
  }
  puts "OT_FIXED_PLACE vm_cp_re: [dict size $tgt] cells placed by construction ($n column flops, [expr {$nflop-$n}] corner flops, $atport cells at ports, $atflop at flops); global_placement NOT run"
}
if { ![info exists ::env(OT_FP_CLK)] } { set ::env(OT_FP_CLK) ck }
rename global_placement ot_real_global_placement
proc global_placement { args } { ot_re_fixed_place }
