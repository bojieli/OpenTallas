# S81-SERDES-GEN 11-17: ported verbatim from the H17 hand kit (authority_input_local.tcl). Library of ot_auth_input procs used by the boot transport step; its own run is off unless OT_SERDES_AUTH_INPUT_LOCAL=1 is set when it is sourced.
# Private H mechanism: move only existing BUF/INV async-authority input trees.
# No port, FF, clock, net, stage or constraint changes. Default off.
namespace eval ot_auth_input {
 variable b;variable d;variable core;variable macros;variable occ
 proc normalized {n} {string map [list [format %c 92] {}] $n}
 proc wire {i} {regexp {^(BUF|INV|HB|CKBUF|CKINV)} [[$i getMaster] getName]}
 proc rectangle {i} {set z [$i getBBox];list [$z xMin] [$z yMin] [$z xMax] [$z yMax]}
 proc walk {net seen} {
  if {$net eq "NULL" || $net eq {} || [dict exists $seen [$net getName]]} {return [list {} {} {}]}
  dict set seen [$net getName] 1;set buffers {};set leaves {};set other {}
  foreach p [$net getITerms] {
   if {[[$p getMTerm] getIoType] ne "INPUT"} continue
   set i [$p getInst];set n [$i getName]
   if {[wire $i]} {
    dict set buffers $n $i
    foreach q [$i getITerms] {
     if {[[$q getMTerm] getIoType] ne "OUTPUT"} continue
     lassign [walk [$q getNet] $seen] bs ls os
     set buffers [dict merge $buffers $bs];set leaves [dict merge $leaves $ls];set other [dict merge $other $os]
    }
   } elseif {[[$p getMTerm] getName] in {RESETN SETN}} {dict set leaves $n $p
   } else {dict set other "$n/[[$p getMTerm] getName]" $p}
  }
  return [list $buffers $leaves $other]
 }
 proc backward {net seen} {
  if {$net eq "NULL" || $net eq {} || [dict exists $seen [$net getName]]} {return {}}
  dict set seen [$net getName] 1;set out {}
  foreach p [$net getITerms] {
   if {[[$p getMTerm] getIoType] ne "OUTPUT"} continue
   set i [$p getInst];if {![wire $i]} continue
   dict set out [$i getName] $i
   foreach q [$i getITerms] {
    if {[[$q getMTerm] getIoType] ne "INPUT" || [[$q getMTerm] getName] in {VDD VSS VPWR VGND}} continue
    set out [dict merge $out [backward [$q getNet] $seen]]
   }
  }
  return $out
 }
 proc exclusive {i targets} {
  set leaves {};set other {}
  foreach p [$i getITerms] {
   if {[[$p getMTerm] getIoType] ne "OUTPUT"} continue
   lassign [walk [$p getNet] {}] b l o;set leaves [dict merge $leaves $l];set other [dict merge $other $o]
  }
  if {[dict size $other] || ![dict size $leaves]} {return {}}
  dict for {n p} $leaves {if {![dict exists $targets $n]} {return {}}}
  return $leaves
 }
 proc overlaps {a b} {lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1;expr {$x0<$u1&&$x1>$u0&&$y0<$v1&&$y1>$v0}}
 proc occupy {r} {
  variable occ;variable d;set step [expr {5*$d}];lassign $r x0 y0 x1 y1
  for {set x [expr {int(floor($x0/$step))}]} {$x<=[expr {int(floor($x1/$step))}]} {incr x} {
   for {set y [expr {int(floor($y0/$step))}]} {$y<=[expr {int(floor($y1/$step))}]} {incr y} {dict lappend occ "$x,$y" $r}
  }
 }
 proc free {r} {
  variable occ;variable d;variable core;variable macros
  lassign $r x0 y0 x1 y1;lassign $core a b c e
  if {$x0<$a||$y0<$b||$x1>$c||$y1>$e} {return 0}
  foreach box $macros {if {[overlaps $r $box]} {return 0}}
  set step [expr {5*$d}]
  for {set x [expr {int(floor($x0/$step))}]} {$x<=[expr {int(floor($x1/$step))}]} {incr x} {
   for {set y [expr {int(floor($y0/$step))}]} {$y<=[expr {int(floor($y1/$step))}]} {incr y} {
    if {![dict exists $occ "$x,$y"]} continue
    foreach box [dict get $occ "$x,$y"] {if {[overlaps $r $box]} {return 0}}
   }
  }
  return 1
 }
 proc run {} {
  variable b;variable d;variable core;variable macros;variable occ
  set b [ord::get_db_block];set d [expr {double([$b getDbUnitsPerMicron])}]
  set lock {};set rst {}
  foreach i [$b getInsts] {
   set n [normalized [$i getName]]
   if {![string match DFF* [[$i getMaster] getName]]} continue
   foreach p [$i getITerms] {
    if {[[$p getMTerm] getName] ne "RESETN"} continue
    if {[regexp {g_locksafe[.]u_hold[.]lock_sync} $n]} {dict set lock [$i getName] $p}
    if {[regexp {g_locksafe[.]u_hold[.]rst_sync} $n]} {dict set rst [$i getName] $p}
   }
  }
  if {[dict size $lock]!=2||[dict size $rst]!=2} {error "OT_AUTH_INPUT expected2lock/2rst sync loads, got[dict size $lock]/[dict size $rst]"}
  set port {}
  foreach p [$b getBTerms] {if {[regexp {^io_pma_lock(?:.0.)?$} [normalized [$p getName]]]} {if {$port ne {}} {error "OT_AUTH_INPUT multipleio_pma_lockports"};set port $p}}
  if {$port eq {}} {error "OT_AUTH_INPUT io_pma_lock input missing"}
  lassign [walk [$port getNet] {}] lockbuf lockleaves other
  if {[dict size $other]||[lsort [dict keys $lockleaves]] ne [lsort [dict keys $lock]]} {error "OT_AUTH_INPUT portload identity mismatch actual=[dict keys $lockleaves], other=[dict keys $other]"}
  set rstbuf {}
  dict for {n p} $rst {set rstbuf [dict merge $rstbuf [backward [$p getNet] {}]]}
  set buffers {};set targets {};set tags {}
  foreach tag {lock rst} {
   set bs [expr {$tag eq "lock" ? $lockbuf : $rstbuf}]
   set ts [expr {$tag eq "lock" ? $lock : $rst}]
   dict for {n i} $bs {
    set leaves [exclusive $i $ts]
    if {![dict size $leaves]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_AUTH_INPUT fixed inputbuffer cannotmove $n"}
    dict set buffers $n $i;dict set targets $n $leaves;dict set tags $n $tag
   }
  }
  if {[dict size $buffers]<[dict size $lockbuf]} {error "OT_AUTH_INPUT notalllockbuffers exclusive toits2syncloads"}
  set c [$b getCoreArea];set core [list [$c xMin] [$c yMin] [$c xMax] [$c yMax]]
  set macros {};set occ {};set halo [expr {8.64*$d}]
  foreach i [$b getInsts] {
   if {[[$i getMaster] isBlock]} {lassign [rectangle $i] mx0 my0 mx1 my1;lappend macros [list [expr {$mx0-$halo}] [expr {$my0-$halo}] [expr {$mx1+$halo}] [expr {$my1+$halo}]];continue}
   if {![dict exists $buffers [$i getName]]} {occupy [rectangle $i]}
  }
  set moves {};set maxmove 0.;set counts [dict create lock 0 rst 0]
  dict for {n i} $buffers {
   set leaves [dict get $targets $n];set ax 0.;set ay 0.
   dict for {ln p} $leaves {
    lassign [$p getAvgXY] ok x y
    if {!$ok} {error "OT_AUTH_INPUT targetpin geometrymissing $ln"}
    set ax [expr {$ax+$x}];set ay [expr {$ay+$y}]
   }
   set ax [expr {round($ax/[dict size $leaves]/(.054*$d))*.054*$d}]
   set ay [expr {round($ay/[dict size $leaves]/(.27*$d))*.27*$d}]
   set m [$i getMaster];set w [$m getWidth];set h [$m getHeight];set found {}
   for {set radius 0} {$radius<=120 && ![llength $found]} {incr radius} {
    set dx [expr {$radius*.54*$d}];set dy [expr {$radius*.27*$d}]
    foreach xy [list [list $ax [expr {$ay-$dy}]] [list $ax [expr {$ay+$dy}]] [list [expr {$ax+$dx}] $ay] [list [expr {$ax-$dx}] $ay] [list [expr {$ax+$dx}] [expr {$ay-$dy}]] [list [expr {$ax-$dx}] [expr {$ay-$dy}]]] {
     lassign $xy x y;set box [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
     if {![free $box]} continue
     occupy $box;set found [list $i $x $y];break
    }
   }
   if {![llength $found]} {error "OT_AUTH_INPUT no vacant macro/halo-safe site for $n"}
   lassign [$i getLocation] ox oy;lassign $found ii x y;set delta [expr {(abs($x-$ox)+abs($y-$oy))/$d}]
   if {$delta>$maxmove} {set maxmove $delta}
   lappend moves $found;dict incr counts [dict get $tags $n]
  }
  foreach move $moves {lassign $move i x y;$i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED}
  puts "OT_AUTH_INPUT moved_BUF_INV=[llength $moves] lock=[dict get $counts lock] rst_exclusive=[dict get $counts rst] max_move_um=$maxmove; exact2lock+2rstFFloads, allports/FFs/nets/clocks/FIRM preserved"
  puts "OT_AUTH_INPUT sharedRSTtrunk untouched; maxdelay833/inputdelay policy unchanged; DPL+actualIOlockSTA stillrequired"
 }
}
if {[info exists ::env(OT_SERDES_AUTH_INPUT_LOCAL)] && $::env(OT_SERDES_AUTH_INPUT_LOCAL) eq "1"} {ot_auth_input::run}
