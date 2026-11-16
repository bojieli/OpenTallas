# Opt-in S81 AM_FACE3 + RELAY4 placement on the existing native column.
# Same registers/edges as RTL; no constraints or data/clock nets are changed.
# The initial E phase pair remains short. Metadata arithmetic/FFs sit beside
# its four recovered-clock header sources; four full-cycle rows span to SYN.
if {![info exists ::env(OT_S81_RCK4_FACE)] || $::env(OT_S81_RCK4_FACE) ne "1"} {
 source [file join [file dirname [info script]] txl_mid.tcl]
 return
}
set rck_save_mid [expr {[info exists ::env(OT_TXL_MID)] ? $::env(OT_TXL_MID) : "0"}]
set rck_save_chains [expr {[info exists ::env(OT_TXL_MID_CHAINS)] ? $::env(OT_TXL_MID_CHAINS) : "u_txl"}]
set ::env(OT_TXL_MID) 0
source [file join [file dirname [info script]] txl_mid.tcl]
set ::env(OT_TXL_MID) 1
set ::env(OT_TXL_MID_CHAINS) {u_txl u_rxf u_dec.u_face_p_d u_dec.u_face_p_v}
ot_txl_mid::run
namespace eval ot_rck4_face {
 proc cone {roots} {
  set cells {};set front $roots
  foreach i $roots {dict set cells [$i getName] $i}
  while {[llength $front]} {
   set next {}
   foreach i $front {
    foreach t [$i getITerms] {
     set pin [[$t getMTerm] getName]
     if {![ $t isInputSignal] || $pin in {CLK CLKN CK CKN RESETN SETN}} continue
     set n [$t getNet]
     if {$n eq "NULL" || [$n getSigType] in {CLOCK POWER GROUND}} continue
     foreach q [$n getITerms] {
      if {![ $q isOutputSignal]} continue
      set j [$q getInst];set name [$j getName];set m [$j getMaster]
      if {[dict exists $cells $name] || [$m isBlock] || [$m isSequential]} continue
      if {[$j getPlacementStatus] in {FIRM LOCKED COVER}} continue
      dict set cells $name $j;lappend next $j
     }
    }
   }
   set front $next
  }
  return $cells
 }
 proc run {} {
  set b [ord::get_db_block];set dbu [expr {double([$b getDbUnitsPerMicron])}]
  set rx {};set parts {}
  foreach i [$b getInsts] {
   set n [$i getName]
   if {[regexp {u_rxf_q\\?\[([0-9]+)\\?\]} $n _ bit] && $bit>=532 && $bit<=543} {dict set rx $bit $i}
   if {[regexp {u_dec\.u_face_am3\.parts\\?\[([0-9]+)\\?\]} $n _ bit]} {dict lappend parts $bit $i}
  }
  if {[dict size $rx]!=12 || [dict size $parts]!=9} {
   error "OT_RCK4_FACE missing actual AM/header shape: RX [dict size $rx]/12 partial [dict size $parts]/9"
  }
  set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set macs {};set halo [expr {8.64*$dbu}]
  foreach i [$b getInsts] {
   if {![[$i getMaster] isBlock]} continue
   set z [$i getBBox]
   lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]
  }
  set moved 0;set ff 0;set max_um 0.0
  for {set g 0} {$g<3} {incr g} {
   set ax 0.0;set ay 0.0
   for {set q 0} {$q<4} {incr q} {
    set i [dict get $rx [expr {532+4*$g+$q}]]
    lassign [$i getLocation] x y;set ax [expr {$ax+$x/4.0}];set ay [expr {$ay+$y/4.0}]
   }
   set roots {}
   for {set q 0} {$q<3} {incr q} {set roots [concat $roots [dict get $parts [expr {3*$g+$q}]]]}
   set cells [cone $roots];set k 0
   foreach n [lsort [dict keys $cells]] {
    set i [dict get $cells $n]
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_RCK4_FACE named AM authority is fixed: $n"}
    set x [expr {$ax+(($k%6)-2.5)*1.08*$dbu}]
    set y [expr {$ay-(12.0+($k/6)*0.54)*$dbu}]
    set p [ot_txl_mid::nearest_free $x $y $macs $core [expr {1.08*$dbu}] [expr {100*$dbu}]]
    if {![llength $p]} {error "OT_RCK4_FACE no nearby macro-free site"}
    lassign $p x y;$i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED
    set d [expr {(abs($x-$ax)+abs($y-$ay))/$dbu}]
    if {$d>$max_um} {set max_um $d}
    if {[[$i getMaster] isSequential]} {incr ff}
    incr k;incr moved
   }
  }
  puts "OT_RCK4_FACE actual partial FF $ff groups 3 cells moved $moved max anchor distance [format %.3f $max_um] um"
 }
}
ot_rck4_face::run
set ::env(OT_TXL_MID_CHAINS) {u_dec.u_rck_transport4 u_dec.u_rck_reset4}
ot_txl_mid::run
set ::env(OT_TXL_MID) $rck_save_mid
set ::env(OT_TXL_MID_CHAINS) $rck_save_chains
