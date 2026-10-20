# PVM9 (HBM-PVM9 2026-10-20): 16 compact EXCLUSIVE lane fences for the bind-first PVM (smh_pvm geometry 345.6 x 302.4,
# stack SRAM R180 at 86.4 / 43.2).  r3 GPL failed RSZ-3006: die-spanning valid/reset nets ended on dont-touch kernel pins,
# so the resizer could not buffer them.  Each lane's kernel (3500 protected cells), its kept operand stage u_opr (oa/ob +
# its own valid copy ov_l) and its own reset leaf g_reset_lane[l] are bound to one dbGroup under one dbRegion, so every
# net that ends on that kernel's pins is local to the fence.  Lanes 0-7 sit in the E band (their wd_in face, rd_out face),
# lanes 8-15 in the W band (their wd_in face); 2 columns x 4 rows of 23.76 x 34.56 um per band (sites/rows aligned).
# Placement constraint only: no cell, net, pin, PG or dont-touch change (checked: membership counts, before/after).
set pvm9_b [ord::get_db_block]
set pvm9_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set pvm9_w 23.76; set pvm9_h 34.56
proc pvm9_origin {l} {
  if {$l < 8} {
    set k $l; set top 203.04; set xs {272.16 300.24}
  } else {
    set k [expr {$l - 8}]; set top 250.56; set xs {49.68 21.6}
  }
  return [list [lindex $xs [expr {$k % 2}]] [expr {$top - 34.56 * (($k / 2) + 1)}]]
}
set pvm9_m [dict create]
foreach i [$pvm9_b getInsts] {
  set n [string map {\\ {}} [$i getName]]
  set l -1; set kind ""
  if {[regexp {^u_core\.g_safe\.g_madd\[([0-9]+)\]\.g_fan32\.u_m\.} $n -> l]} { set kind kernel
  } elseif {[regexp {^u_core\.g_safe\.g_madd\[([0-9]+)\]\.u_opr/} $n -> l]} { set kind opr
  } elseif {[regexp {^g_reset_lane\[([0-9]+)\]\.u/} $n -> l]} { set kind leaf
  } elseif {[regexp {^u_core\.g_safe\.g_madd\[([0-9]+)\]\.} $n -> l]} { set kind other }
  if {$kind ne ""} { dict lappend pvm9_m $l [list $kind $i] }
}
if {[dict size $pvm9_m] != 16} { error "PVM9_FENCE lanes [dict keys $pvm9_m]" }
set pvm9_total 0
for {set l 0} {$l < 16} {incr l} {
  lassign [pvm9_origin $l] x0 y0
  set rn pvm9_lane$l
  set r [$pvm9_b findRegion $rn]
  if {$r eq "NULL"} {
    set r [odb::dbRegion_create $pvm9_b $rn]
    $r setRegionType EXCLUSIVE
    odb::dbBox_create $r [expr {round($x0*$pvm9_dbu)}] [expr {round($y0*$pvm9_dbu)}] \
      [expr {round(($x0+$pvm9_w)*$pvm9_dbu)}] [expr {round(($y0+$pvm9_h)*$pvm9_dbu)}]
  }
  set g [$pvm9_b findGroup pvm9_lane${l}_group]
  if {$g eq "NULL"} { set g [odb::dbGroup_create $r pvm9_lane${l}_group] }
  if {[$g getRegion] ne $r} { error "PVM9_FENCE_GROUP_REGION $l" }
  set cnt [dict create kernel 0 opr 0 leaf 0 other 0]; set area 0.0; set added 0
  foreach e [dict get $pvm9_m $l] {
    lassign $e kind i
    dict incr cnt $kind
    set m [$i getMaster]
    set area [expr {$area + double([$m getWidth])*[$m getHeight]/$pvm9_dbu/$pvm9_dbu}]
    set old [$i getRegion]
    if {$old eq "NULL" || [$old getId] != [$r getId]} { $r addInst $i; incr added }
    set og [$i getGroup]
    if {$og eq "NULL" || [$og getId] != [$g getId]} { $g addInst $i }
    if {[[$i getGroup] getId] != [$g getId] || [[$i getRegion] getId] != [$r getId]} { error "PVM9_FENCE_MEMBER [$i getName]" }
  }
  if {[dict get $cnt kernel] != 3500 || [dict get $cnt opr] < 65 || [dict get $cnt leaf] < 1 || [dict get $cnt other] != 0} {
    error "PVM9_FENCE_COUNTS lane $l $cnt"
  }
  set util [expr {$area / ($pvm9_w * $pvm9_h)}]
  if {$util > 0.70} { error "PVM9_FENCE_UTIL lane $l [format %.3f $util]" }
  incr pvm9_total [llength [dict get $pvm9_m $l]]
  puts [format "PVM9_FENCE lane %d box (%.2f %.2f %.2f %.2f) %s area %.1f util %.3f added %d" $l $x0 $y0 \
    [expr {$x0+$pvm9_w}] [expr {$y0+$pvm9_h}] $cnt $area $util $added]
}
puts "PVM9_FENCE_PASS lanes=16 members=$pvm9_total"
