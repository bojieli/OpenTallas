# QC-CORES-1 btab_m0_r7 PRE_GLOBAL_PLACE (GEOM-REVIEW-7 17:30 cond: "per-bank/bounded-density mux regions"): r5 member
# selection UNCHANGED (512 E read-mux cells = 256 AO22 (bank 0/1 select) + 256 AO221 (bank 2/3 + AO22 -> E output register)),
# but instead of ONE inclusive region (GPL packed all 512 into a 6-um band at x 252-258, M2/M3/M5 hot band, 155/167 DRT
# viol at it5) the mux is placed by plan into a BOUNDED-DENSITY GRID: stage A (AO22) in 4 columns over x 255-293, stage B
# (AO221) in 4 columns over x 302-340 (each column 6.48 um wide, 9.72 pitch, 3.24 gap), 8 equal-count row bands per stage
# (32 cells/band, 8/region) ordered by each cell's pin-median target y (A: median of its 2 bank capture flops + its output
# register; B: median of its 2 bank capture flops + its output register; capture/output flops are FIRM here).  Each bit's
# A then B cell sit monotonically W->E between capture flops (x ~235) and the E output register (x ~347): no extra path
# length.  Placement only: no netlist / SDC / clock change.  Regions released before DPL (pre_dpl_r7.tcl).
# ---- r5 header (member selection, unchanged) ----
# QC-SU-BTAB-R5 PRE_GLOBAL_PLACE (GEOM-REVIEW-6 16:23 structural fix (2), "spread the E-column logic into x 255-340"):
# r4 hooks unchanged (pushdown, face pin registers, macro-pin flops anchored FIRM at their SRAM pins), then an INCLUSIVE
# placement region (members must sit inside it, other cells may too) over the empty E area x OT_R5_EL_X0..X1 (255..340),
# y = SRAM rows +- 4.32, for the E-column READ-MUX LOGIC: every combinational cell (not a flop, not INV/BUF/HB: those stay
# with their pin flops) whose input is driven, through at most 2 INV/BUF/HB hops, by an E-face macro-pin capture flop and
# by no W-face one.  r4 measured: 2.4k cells in the one 10-um bin x 230-240 (2010 INVx1 at the pin flops + 512 AO22/AO221
# bank-select read mux); the mux has no reason to sit on the pin column.  Placement only: no netlist / SDC / clock change.
# (r5 try 1 used a partial density blockage at x 237.6-254.9: no effect, the logic sits at x 229-237 among the pin flops.)
source /work/pre_gpl_m0.tcl
set r5b [ord::get_db_block]; set r5u [[ord::get_db_tech] getDbUnitsPerMicron]
proc r5env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set r5x0 [r5env OT_R5_EL_X0 255.0]; set r5x1 [r5env OT_R5_EL_X1 340.0]
set r5ylo 1e9; set r5yhi -1e9; set r5mx 0
foreach i [$r5b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set bb [$i getBBox]; set r5mx [expr {max($r5mx, [$bb xMax])}]
  set r5ylo [expr {min($r5ylo, [$bb yMin] / double($r5u) - 4.32)}]; set r5yhi [expr {max($r5yhi, [$bb yMax] / double($r5u) + 4.32)}]
}
proc r5_isbuf {i} { regexp {^(INV|BUF|HB)} [[$i getMaster] getName] }
proc r5_isff {i} { string match "*DFF*" [[$i getMaster] getName] }
set r5side [dict create]
set f [open $::env(RESULTS_DIR)/ot_macro_pin_flops.txt]
foreach n [split [read $f] "\n"] {
  if {$n eq ""} continue
  set i [$r5b findInst $n]; if {$i eq "NULL"} continue
  set x [lindex [$i getLocation] 0]
  dict set r5side $n [expr {$x > $r5mx ? "E" : "W"}]
}
close $f
# downstream of every macro-pin flop: through <=2 INV/BUF/HB to combinational cells; record the side(s) feeding each cell
set r5feed [dict create]
dict for {n s} $r5side {
  set i [$r5b findInst $n]
  set front {}
  foreach it [$i getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { lappend front [list [$it getNet] 0] } }
  while {[llength $front]} {
    lassign [lindex $front end] net d; set front [lrange $front 0 end-1]
    if {[$net getSigType] in {CLOCK POWER GROUND}} continue
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set j [$it getInst]; if {[[$j getMaster] isBlock] || [r5_isff $j]} continue
      if {[r5_isbuf $j]} {
        if {$d < 2} { foreach o [$j getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [list [$o getNet] [expr {$d + 1}]] } } }
        continue
      }
      dict lappend r5feed [$j getName] $s
    }
  }
}
set r5mem {}
dict for {n ss} $r5feed {
  if {[lsearch $ss W] >= 0} continue
  set j [$r5b findInst $n]; if {[$j getPlacementStatus] in {FIRM LOCKED}} continue
  lappend r5mem $j
}

# ---- r7 bounded-density grid ----
set ::r7u $r5u
proc r7_fy {i} { return [expr {[lindex [$i getLocation] 1] / double($::r7u) + 0.135}] }
proc r7_med {l} { set l [lsort -real $l]; set n [llength $l]; if {$n == 0} {return ""}; if {$n % 2} {return [lindex $l [expr {$n/2}]]}; return [expr {([lindex $l [expr {$n/2-1}]] + [lindex $l [expr {$n/2}]]) / 2.0}] }
# pin-median target: y of the FIRM flops this cell touches directly or through <=2 INV/BUF/HB hops (inputs: drivers; output: sinks)
proc r7_target {j} {
  set ys {}
  foreach it [$j getITerms] {
    set net [$it getNet]; if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} continue
    if {[$it isInputSignal]} {
      set cur $net
      for {set h 0} {$h < 3} {incr h} {
        set drv ""; foreach jt [$cur getITerms] { if {[$jt isOutputSignal]} { set drv [$jt getInst] } }
        if {$drv eq ""} break
        if {[r5_isff $drv]} { if {[$drv getPlacementStatus] in {FIRM LOCKED}} { lappend ys [r7_fy $drv] }; break }
        if {![r5_isbuf $drv]} break
        set nx ""; foreach jt [$drv getITerms] { if {[$jt isInputSignal] && [$jt getNet] ne "NULL"} { set nx [$jt getNet] } }
        if {$nx eq ""} break; set cur $nx
      }
    } elseif {[$it isOutputSignal]} {
      set front [list [list $net 0]]
      while {[llength $front]} {
        lassign [lindex $front end] n2 d; set front [lrange $front 0 end-1]
        foreach jt [$n2 getITerms] {
          if {![$jt isInputSignal]} continue; set k [$jt getInst]
          if {[r5_isff $k]} { if {[$k getPlacementStatus] in {FIRM LOCKED}} { lappend ys [r7_fy $k] }; continue }
          if {[r5_isbuf $k] && $d < 2} { foreach o [$k getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [list [$o getNet] [expr {$d+1}]] } } }
          # AO22 -> AO221: follow one more stage to the output register
          if {[string match AO221* [[$k getMaster] getName]] && $d == 0} { foreach o [$k getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [list [$o getNet] 1] } } }
        }
      }
    }
  }
  return [r7_med $ys]
}
proc r7_snapx {x} { return [expr {4.32 + round(($x - 4.32) / 0.054) * 0.054}] }
proc r7_snapy {y} { return [expr {4.32 + round(($y - 4.32) / 0.27) * 0.27}] }
set R7_NCOL [r5env OT_R7_NCOL 4]; set R7_NROW [r5env OT_R7_NROW 8]; set R7_CW 6.48; set R7_CP 9.72
set R7_X0 [dict create A [r5env OT_R7_AX0 255.04] B [r5env OT_R7_BX0 302.0]]
set r7stage [dict create A {} B {}]; set r7miss 0
foreach j $r5mem {
  set m [[$j getMaster] getName]
  set st [expr {[string match AO221* $m] ? "B" : "A"}]
  set t [r7_target $j]; if {$t eq ""} { incr r7miss; set t [expr {($r5ylo + $r5yhi) / 2.0}] }
  dict lappend r7stage $st [list $t $j]
}
set r7log [open $::env(RESULTS_DIR)/r7_mux_grid.txt w]
set r7nreg 0
foreach st {A B} {
  set L [lsort -real -index 0 [dict get $r7stage $st]]; set n [llength $L]
  if {$n == 0} continue
  set per [expr {int(ceil($n / double($R7_NROW)))}]
  set bands {}
  for {set b 0} {$b < $R7_NROW} {incr b} { set sub [lrange $L [expr {$b*$per}] [expr {min($n, ($b+1)*$per) - 1}]]; if {[llength $sub]} { lappend bands $sub } }
  set nb [llength $bands]
  # band edges: midpoints between neighbouring bands' extreme targets; outer edges pad 2.7 um; min band height 2.7 um
  set edges {}
  for {set b 0} {$b <= $nb} {incr b} {
    if {$b == 0} { lappend edges [expr {[lindex [lindex [lindex $bands 0] 0] 0] - 2.7}]; continue }
    if {$b == $nb} { lappend edges [expr {[lindex [lindex [lindex $bands end] end] 0] + 2.7}]; continue }
    lappend edges [expr {([lindex [lindex [lindex $bands [expr {$b-1}]] end] 0] + [lindex [lindex [lindex $bands $b] 0] 0]) / 2.0}]
  }
  for {set b 0} {$b < $nb} {incr b} {
    set y0 [r7_snapy [lindex $edges $b]]; set y1 [r7_snapy [lindex $edges [expr {$b+1}]]]
    if {$y1 - $y0 < 2.7} { set c [expr {($y0+$y1)/2.0}]; set y0 [r7_snapy [expr {$c-1.35}]]; set y1 [expr {$y0 + 2.7}] }
    set cells [lindex $bands $b]
    for {set c 0} {$c < $R7_NCOL} {incr c} {
      set x0 [r7_snapx [expr {[dict get $R7_X0 $st] + $c * $R7_CP}]]; set x1 [r7_snapx [expr {$x0 + $R7_CW}]]
      set mem {}; set ci 0
      foreach e $cells { if {$ci % $R7_NCOL == $c} { lappend mem [lindex $e 1] }; incr ci }
      if {![llength $mem]} continue
      set nm "r7_mux_${st}_${b}_${c}"
      set r [odb::dbRegion_create $r5b $nm]; $r setRegionType INCLUSIVE
      odb::dbBox_create $r [expr {round($x0 * $r5u)}] [expr {round($y0 * $r5u)}] [expr {round($x1 * $r5u)}] [expr {round($y1 * $r5u)}]
      set g [odb::dbGroup_create $r $nm]; $g setType VOLTAGE_DOMAIN
      foreach j $mem { $g addInst $j; puts $r7log "$nm [$j getName] [format "%.2f %.2f %.2f %.2f" $x0 $y0 $x1 $y1]" }
      incr r7nreg
    }
  }
}
close $r7log
set fo [open $::env(RESULTS_DIR)/r5_e_logic.txt w]; foreach j $r5mem { puts $fo [$j getName] }; close $fo
puts [format "R7_MUX_GRID %d read-mux cells (A %d / B %d) in %d INCLUSIVE regions (%d cols x %d bands per stage, A x0 %.2f, B x0 %.2f); %d cells without a FIRM-flop target; E/W pin flops %d/%d" [llength $r5mem] [llength [dict get $r7stage A]] [llength [dict get $r7stage B]] $r7nreg $R7_NCOL $R7_NROW [dict get $R7_X0 A] [dict get $R7_X0 B] $r7miss [llength [lsearch -all [dict values $r5side] E]] [llength [lsearch -all [dict values $r5side] W]]]
