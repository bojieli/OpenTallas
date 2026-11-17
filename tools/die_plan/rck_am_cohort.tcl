# Opt-in S81 header/AM same-clock cohort. Only clock leaf connections change.
# The baseline leaf-affinity checks retain clock/gating identity, radius and cap.
if {![info exists ::env(OT_S81_RCK_AM_COHORT)] || $::env(OT_S81_RCK_AM_COHORT) ne "1"} { return }
if {![llength [info procs la_try]]} { error "OT_RCK_AM_COHORT requires enabled baseline leaf_affinity" }
global la_ck la_moved la_groot_c
# AM scope only: trace to the actual clock/gating root, without the generic
# walker's 64-buffer cutoff. A visited set rejects loops; INV parity is retained.
proc ot_rck_am_root {net} {
 set seen {}; set parity 0
 while {1} {
  set name [$net getName]
  if {[dict exists $seen $name]} { error "OT_RCK_AM_COHORT clock loop at $name" }
  dict set seen $name 1
  set drv [la_drv $net]
  if {$drv eq ""} { return "port:$name:$parity" }
  if {![la_is_bufinv $drv]} { return "inst:[$drv getName]:$parity" }
  if {[regexp {INV} [[$drv getMaster] getName]]} { set parity [expr {1-$parity}] }
  set inputs {}
  foreach pin [$drv getITerms] {
   if {[$pin isInputSignal] && [$pin getNet] ne "NULL"} { lappend inputs [$pin getNet] }
  }
  if {[llength $inputs]!=1} { error "OT_RCK_AM_COHORT ambiguous buffer clock inputs: [$drv getName]" }
  set net [lindex $inputs 0]
 }
}

# S81-SERDES-R2 G3 (11-16): la_try picks the leaf with most members; when that leaf's driver is > OT_LEAF_AFF_UM
# from a member ("far", G3 CTS 11-16) try every member leaf, nearest driver to the cohort centroid first, with the
# same clock/gating/cap and unchanged OT_LEAF_AFF_UM radius checks. Only clock leaf connections change.
proc ot_rck_am_near {mem} {
 global la_ck la_fo la_cap la_ronly la_moved la_blk la_um la_dbu la_maxg
 if {![la_same_clock $mem]} {return clock}
 if {[llength $mem]>$la_maxg} {return big}
 set r [expr {$la_um * $la_dbu}]
 set sx 0; set sy 0
 foreach m $mem { lassign [la_xy [[dict get $la_ck $m] getInst]] x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}] }
 set cx [expr {$sx/[llength $mem]}]; set cy [expr {$sy/[llength $mem]}]
 set cand {}
 foreach m $mem {
  set net [la_leaf $m]; if {$net eq "NULL"} continue
  set drv [la_drv $net]; if {$drv eq "" || [$net getSigType] ne "CLOCK"} continue
  lassign [la_xy $drv] dx dy
  lappend cand [list [expr {abs($dx-$cx)+abs($dy-$cy)}] [$net getName] $dx $dy]
 }
 set cand [lsort -unique -index 1 $cand]
 foreach c [lsort -real -index 0 $cand] {
  lassign $c dc nn dx dy
  set net [$la_blk findNet $nn]; set g0 [la_groot $net]; set mv {}; set worst 0; set bad ""
  foreach m $mem {
   set it [dict get $la_ck $m]
   lassign [la_xy [$it getInst]] x y; set d [expr {abs($x-$dx)+abs($y-$dy)}]; if {$d>$worst} { set worst $d }
   if {[[$it getNet] getName] eq $nn} continue
   if {$d > $r} { set bad far; break }
   if {[la_groot [$it getNet]] ne $g0} { set bad gate; break }
   lappend mv $it
  }
  if {$bad eq "" && [dict get $la_fo $nn] + [llength $mv] > $la_cap} { set bad cap }
  puts "OT_RCK_AM_NEAR leaf $nn driver_to_centroid [format %.1f [expr {double($dc)/$la_dbu}]] um worst_member [format %.1f [expr {double($worst)/$la_dbu}]] um verdict [expr {$bad eq "" ? "ok" : $bad}]"
  if {$bad ne ""} continue
  if {!$la_ronly} {
   foreach it $mv { set old [$it getNet]; dict incr la_fo [$old getName] -1; $it disconnect; $it connect $net; dict incr la_fo $nn; incr la_moved }
  }
  return moved
 }
 return far
}
set am_hdr {}; set am_parts {}
foreach n [dict keys $la_ck] {
 if {[regexp {u_rxf_q\\?\[([0-9]+)\\?\]} $n _ bit] && $bit>=532 && $bit<=543} { dict set am_hdr $bit $n }
 if {[regexp {u_dec\.u_face_am3\.parts\\?\[([0-9]+)\\?\]} $n _ bit]} { dict lappend am_parts $bit $n }
}
if {[dict size $am_hdr]!=12 || [dict size $am_parts]!=9} {
 error "OT_RCK_AM_COHORT missing actual header/AM FF: [dict size $am_hdr]/12, [dict size $am_parts]/9"
}
set am_before $la_moved; set am_groups 0
for {set g 0} {$g<3} {incr g} {
 set members {}
 for {set q 0} {$q<4} {incr q} { lappend members [dict get $am_hdr [expr {532+4*$g+$q}]] }
 for {set q 0} {$q<3} {incr q} {
  set part [dict get $am_parts [expr {3*$g+$q}]]
  if {[llength $part]!=1} { error "OT_RCK_AM_COHORT ambiguous AM FF: $part" }
  lappend members [lindex $part 0]
 }
 set roots {};set leaves {}
 foreach name $members {
  set net [[dict get $la_ck $name] getNet]
  set root [ot_rck_am_root $net]
  dict set roots $root 1;dict set leaves [$net getName] $root
 }
 if {[dict size $roots]!=1} { error "OT_RCK_AM_COHORT group $g has different actual clock/gating roots: [dict keys $roots]" }
 # Cache only the selected leaves after the complete root/parity proof.
 dict for {leaf root} $leaves { dict set la_groot_c $leaf $root }
 puts "OT_RCK_AM_COHORT group $g actual_root [lindex [dict keys $roots] 0]"
 set verdict [la_try $members]
 if {$verdict eq "far"} {set verdict [ot_rck_am_near $members]}
 if {$verdict ni {moved ok}} { error "OT_RCK_AM_COHORT group $g rejected by baseline clock/gating/radius/cap check: $verdict" }
 incr am_groups
 puts "OT_RCK_AM_COHORT group $g FF [llength $members] status $verdict"
}
puts "OT_RCK_AM_COHORT groups $am_groups header_FF12 AM_FF9 clock_sinks_moved [expr {$la_moved-$am_before}] data_stages_unchanged"
