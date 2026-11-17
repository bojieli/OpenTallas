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
 if {$verdict ni {moved ok}} { error "OT_RCK_AM_COHORT group $g rejected by baseline clock/gating/radius/cap check: $verdict" }
 incr am_groups
 puts "OT_RCK_AM_COHORT group $g FF [llength $members] status $verdict"
}
puts "OT_RCK_AM_COHORT groups $am_groups header_FF12 AM_FF9 clock_sinks_moved [expr {$la_moved-$am_before}] data_stages_unchanged"
