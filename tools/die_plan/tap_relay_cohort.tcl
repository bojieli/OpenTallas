# QC-TTC-R2 TAP-RELAY-COHORT 11-23 (default off, OT_TAP_RELAY_COHORT=1): consecutive reset/run relays of one chain that sit at the
# SAME site (<= OT_TAP_RELAY_COHORT_UM, default 24 um) share one clock tap: the launching relay takes the tap of the relay it feeds,
# walked from the chain tail, so a zero-logic relay pair never launches and captures on two trees.  Why: the cap pass evicts relays
# from an over-full tap one by one, the pair pass never moves a relay, and ct_follow runs only with tap groups (QC tt_ctlm probe
# p_pofix: u_rrl_78 -> u_rrl_79 1.6 um apart on t46 / t26, FF hold -43.26; u_srl_141 -> u_srl_142 2.7 um on t65 / t47, -29.87).
# Clock pins only: no data, reset, cell or timing change.  Long relay hops (a different site) keep their own tap.
namespace eval ::ot_tap_relay {
 proc run {} {
  global ct_taps
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set lim [expr {([info exists ::env(OT_TAP_RELAY_COHORT_UM)] ? $::env(OT_TAP_RELAY_COHORT_UM) : 24.0) * $dbu}]
  set tapn {}
  foreach tp $ct_taps { dict set tapn [[lindex $tp 1] getName] [lindex $tp 1] }
  set rel {}
  foreach inst [$blk getInsts] {
   if {![regexp {(^|[/.])(u_[rs]rl_[0-9]+)(_[rgb])?[/.]} [$inst getName]] || ![string match DFF* [[$inst getMaster] getName]]} continue
   set ck [$inst findITerm CLK]
   if {$ck eq "NULL" || [$ck getNet] eq "NULL" || ![dict exists $tapn [[$ck getNet] getName]]} continue
   dict set rel [$inst getName] [list $inst $ck]
  }
  # feed edges relay -> relay through buffers/inverters only
  set succ {}
  dict for {n row} $rel {
   lassign $row inst ck
   set todo {}; set seen {}
   foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [list [$o getNet] 0] } }
   while {[llength $todo]} {
    lassign [lindex $todo 0] net d; set todo [lrange $todo 1 end]
    if {[dict exists $seen [$net getName]]} continue
    dict set seen [$net getName] 1
    foreach s [$net getITerms] {
     if {![$s isInputSignal]} continue
     set si [$s getInst]; set sn [$si getName]
     if {[dict exists $rel $sn] && [[$s getMTerm] getName] eq "D"} {
      lassign [$inst getLocation] x0 y0; lassign [$si getLocation] x1 y1
      if {abs($x0-$x1)+abs($y0-$y1) <= $lim} { dict lappend succ $n $sn }
      continue
     }
     if {$d < 3 && [regexp {^(BUF|INV|HB|CKINV)} [[$si getMaster] getName]]} {
      foreach o [$si getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [list [$o getNet] [expr {$d+1}]] } }
     }
    }
   }
  }
  set moved 0; set pairs 0; set done {}; set cut 0
  proc visit {n} {
   upvar 1 rel rel succ succ done done moved moved pairs pairs cut cut
   if {[dict exists $done $n]} return
   dict set done $n 1
   if {![dict exists $succ $n]} return
   foreach s [dict get $succ $n] { visit $s }
   # a fork with successors on several taps keeps the tap of the nearest (first) successor
   set s [lindex [dict get $succ $n] 0]
   incr pairs
   set want [[lindex [dict get $rel $s] 1] getNet]
   set ck [lindex [dict get $rel $n] 1]
   if {[[$ck getNet] getName] ne [$want getName]} { $ck disconnect; $ck connect $want; incr moved }
   foreach x [lrange [dict get $succ $n] 1 end] {
    if {[[[lindex [dict get $rel $x] 1] getNet] getName] ne [$want getName]} { incr cut }
   }
  }
  foreach n [dict keys $rel] { visit $n }
  puts "OT_TAP_RELAY relays [dict size $rel], same-site feeding relays $pairs, clock pins moved $moved, forks left cross-tap $cut (site [expr {$lim/$dbu}] um)"
 }
}
::ot_tap_relay::run
