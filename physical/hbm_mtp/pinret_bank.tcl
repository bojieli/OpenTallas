# PRE_GLOBAL_PLACE hook (drive-0849, 2026-10-09): out_flop_at_pins.tcl extended to INPUT ports.  For every output port its
# launching flop, and for every input port its single capturing flop (the port net -- through up to three single-fanout
# INV / BUF stages -- reaches exactly one DFF D pin), is placed FIRM just inside the core on the pin's own edge, in up to
# 4 staggered columns by pin order.  Why: low-utilisation die-slot outlines (qfd_sp_constants_sequencer_sys 777.6 x 1000
# at ~1 %, qfd_sp_res_ser) let timing-driven GPL pull pin flops into the central logic, so pin -> flop and flop -> pin
# become 200-760 ps wires (ICUT 155370387: vm_rq -> line -514.8, c_data -309; res_ser r2q: i_addr -> c_addr 535 ps wire).
# The pin flop then carries the distance on a reg -> reg path with a full cycle.  out_flop_release.tcl (PRE_DETAIL_PLACE)
# returns them to PLACED for DPL (same list file).  Placement only, 0 cycles.
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

# The returned handshake is internal but belongs beside its receiving ready pin.
set returned_count 0
foreach net [$ot_blk getNets] {
 if {![regexp {g_pinret[./]u_(hw|fn)[./]returned$} [$net getName] _ unit]} continue
 set d [ot_of_drv $net]; if {$d eq ""} continue
 set ff [$d getInst]; if {![ot_of_isff $ff]} continue
 if {[dict exists $ot_seen [$ff getName]]} continue
 dict set ot_seen [$ff getName] 1
 set port [expr {$unit eq "hw" ? "host_wr_ready" : "fence_ready"}]
 set bt [$ot_blk findBTerm $port]; set bb [$bt getBBox]
 set px [expr {double([$bb xMin]+[$bb xMax])/2.0/$ot_dbu}]
 set py [expr {double([$bb yMin]+[$bb yMax])/2.0/$ot_dbu}]
 if {$px <= $cx0} {set side L} elseif {$px >= $cx1} {set side R} elseif {$py <= $cy0} {set side B} else {set side T}
 set pos [expr {($side eq "L" || $side eq "R") ? $py : $px}]
 lappend cand [list $side $pos $ff $px $py INPUT]
 incr returned_count
}
if {$returned_count != 2} {error "PINRET expected two handshake-return capture flops, got $returned_count"}
# Assign real row/site coordinates and disjoint sites before making cells FIRM.
# Fence has no macros. Reserve a <=16um bank at each face, and hold it through
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
 if {!$placed} {error "PINRET no legal pin-bank site for [$ff getName]"}
}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list {puts $fh $n}; close $fh
puts "PINRET_LEGAL_BANK anchored $count pin flops at disjoint row sites"
if {$count<4113} {error "PINRET output registers missing from mapped pin bank"}
