# Opt-in W2 own-pin register seats. No RTL or timing changes.
# Register-to-pin and pin-to-register nets retain the same exact contract.
# Legal disjoint sites, <=16um inward and <=12um lateral, FIRM through DPL.
# Release to PLACED after DPL so later timing repair remains available.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]; set cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set cy0 [expr {double([$ot_core yMin]) / $ot_dbu}]; set cy1 [expr {double([$ot_core yMax]) / $ot_dbu}]
set ot_gap [expr {[info exists ::env(OT_OFLOP_GAP)] ? $::env(OT_OFLOP_GAP) : 1.0}]
proc ot_of_drv {net} {
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return $it } }
  return ""
}
proc ot_of_isff {inst} { return [string match "DFF*" [[$inst getMaster] getName]] }
proc ot_of_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "INV*" $m] || [string match "BUF*" $m]}] }
# the single input-signal sink of a net (or "" if 0 or > 1 sinks)
proc ot_of_sink {net} {
  set s ""
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    if {$s ne ""} { return "" }
    set s $it
  }
  return $s
}
set ot_list {}; set ot_n 0; set ot_ni 0; set ot_skip 0
set cand {}
set ot_seen [dict create]
foreach bt [$ot_blk getBTerms] {
  set io [$bt getIoType]
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set ff ""
  if {$io eq "OUTPUT"} {
    set d [ot_of_drv $net]; if {$d eq ""} { incr ot_skip; continue }
    set inst [$d getInst]
    for {set hop 0} {$hop < 4} {incr hop} {
      if {[ot_of_isff $inst]} { set ff $inst; break }
      if {![ot_of_isbuf $inst]} break
      set nxt ""
      foreach it [$inst getITerms] {
        if {![$it isInputSignal]} continue
        set n2 [$it getNet]; if {$n2 eq "NULL"} continue
        set d2 [ot_of_drv $n2]
        if {$d2 ne "" && [llength [$n2 getITerms]] == 2} { set nxt [$d2 getInst] }
      }
      if {$nxt eq ""} break
      set inst $nxt
    }
  } elseif {$io eq "INPUT"} {
    if {[$net getSigType] eq "CLOCK"} continue
    set s [ot_of_sink $net]; if {$s eq ""} { incr ot_skip; continue }
    for {set hop 0} {$hop < 4} {incr hop} {
      set inst [$s getInst]
      if {[ot_of_isff $inst]} {
        if {[[$s getMTerm] getName] eq "D"} { set ff $inst }
        break
      }
      if {![ot_of_isbuf $inst]} break
      set on ""
      foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
      if {$on eq "" || $on eq "NULL"} break
      set s [ot_of_sink $on]; if {$s eq ""} break
    }
  } else { continue }
  if {$ff eq ""} { incr ot_skip; continue }
  set fn [$ff getName]
  if {[dict exists $ot_seen $fn]} continue
  dict set ot_seen $fn 1
  set bb [$bt getBBox]
  set px [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $ot_dbu}]
  set py [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $ot_dbu}]
  if {$px <= $cx0} { set side L } elseif {$px >= $cx1} { set side R } elseif {$py <= $cy0} { set side B } else { set side T }
  lappend cand [list $side [expr {($side eq "L" || $side eq "R") ? $py : $px}] $ff $px $py $io]
}

# Assign real row/site coordinates and disjoint sites before making cells FIRM.
# W2 station has no macros. Reserve a <=16um bank at each face, and hold it through
# detailed placement. Cells released before DPL previously drifted 150um.
set rows {}
foreach row [$ot_blk getRows] {
 if {[$row getSiteCount] == 0} continue
 set bb [$row getBBox]
 lappend rows [list [$bb yMin] [$bb xMin] [$bb xMax] [$row getSite] [$row getOrient]]
}
set used [dict create]
set count 0
foreach c [lsort -real -index 1 $cand] {
 lassign $c side pos ff px py io
 set width [[$ff getMaster] getWidth]; set height [[$ff getMaster] getHeight]
 set targetx [expr {round($px*$ot_dbu-$width/2)}]
 set targety [expr {round($py*$ot_dbu-$height/2)}]
 set options {}
 foreach row $rows {
  lassign $row y x0 x1 site orient
  set sh [$site getHeight]; set sw [$site getWidth]
  if {$height!=$sh} continue
  if {$side eq "T"} {set distance [expr {round($cy1*$ot_dbu)-($y+$height)}]} elseif {$side eq "B"} {
   set distance [expr {$y-round($cy0*$ot_dbu)}]
  } else {set distance [expr {abs($y-$targety)}]}
  if {$distance<0 || $distance>16*$ot_dbu} continue
  lappend options [linsert $row 0 $distance]
 }
 set placed 0
 foreach option [lsort -integer -index 0 $options] {
  lassign $option distance y x0 x1 site orient
  set sw [$site getWidth]; set sites [expr {int(ceil(double($width)/$sw))}]
  if {$side eq "L"} {set want [expr {$x0+round($ot_gap*$ot_dbu)}]} elseif {$side eq "R"} {
   set want [expr {$x1-$width-round($ot_gap*$ot_dbu)}]
  } else {set want $targetx}
  set base [expr {int(round(double($want-$x0)/$sw))}]
  set maxshift [expr {int(12*$ot_dbu/$sw)}]
  for {set shift 0} {$shift<=$maxshift && !$placed} {incr shift} {
   foreach signed [list $shift [expr {-$shift}]] {
    set begin [expr {$base+$signed}]; set x [expr {$x0+$begin*$sw}]
    if {$x<$x0 || $x+$width>$x1} continue
    set free 1
    for {set k $begin} {$k<$begin+$sites} {incr k} {
     if {[dict exists $used "$y:$k"]} {set free 0; break}
    }
    if {!$free} continue
    for {set k $begin} {$k<$begin+$sites} {incr k} {dict set used "$y:$k" 1}
    $ff setOrient $orient; $ff setLocation $x $y; $ff setPlacementStatus FIRM
    lappend ot_list [$ff getName]; incr count; set placed 1; break
   }
  }
  if {$placed} break
 }
 if {!$placed} {error "W2_PIN_BANK no legal pin-bank site for [$ff getName]"}
}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list {puts $fh $n}; close $fh
puts "W2_PIN_BANK_LEGAL_BANK anchored $count pin flops at disjoint row sites"
if {$count==0} {error "W2_PIN_BANK output registers missing from mapped pin bank"}
