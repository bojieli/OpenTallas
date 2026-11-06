# Default-off BODY metadata clock-cohort report. Never rewires or moves cells.
# Uses exact UID members, existing same-root/phase helpers and actual data arcs.
if {![info exists ::env(OT_BODY_CHAIN_CANARY)] || $::env(OT_BODY_CHAIN_CANARY) ne "1"} {return}
if {![info exists ::env(OT_BODY_CHAIN_DIR)]} {error "BODY_CANARY missing typed cohort directory"}
set ::env(OT_LEAF_AFF_REPORT_ONLY) 1
source [file join [file dirname [info script]] leaf_affinity.tcl]
proc bc_norm {s} {return [string map [list "\\" ""] $s]}
set bc_actual {};dict for {name it} $la_ck {dict set bc_actual [bc_norm $name] $name}
set bc_members {};set bc_stage {};set bc_dir $::env(OT_BODY_CHAIN_DIR)
set f [open [file join $bc_dir members.tsv] r];gets $f header
if {$header ne "instance\tmaster\tclock_pin\tfamily\tstage\tbit\tnative_clock\treset\tenable"} {error "BODY_CANARY invalid member schema"}
while {[gets $f line]>=0} {
 lassign [split $line "\t"] id master pin family stage bit nativeclock reset enable
 if {$family ne "vm_meta_pipe" || $stage<0 || $stage>90 || $bit<0 || $bit>131 || $nativeclock ne "clk_control" || $reset ne "none" || $enable ne "unconditional"} {error "BODY_CANARY invalid typed native member $id"}
 if {![dict exists $bc_actual $id] || [dict exists $bc_members $id] || [dict exists $bc_stage $bit:$stage]} {error "BODY_CANARY missing/duplicate exact member $id"}
 set name [dict get $bc_actual $id];set it [dict get $la_ck $name];set inst [$it getInst]
 if {[[$inst getMaster] isBlock] || [[$inst getMaster] getName] ne $master || $master ne "DFFHQNx1_ASAP7_75t_R" || [[$it getMTerm] getName] ne $pin || $pin ne "CLK"} {error "BODY_CANARY master/clock identity $id"}
 if {[la_groot [$it getNet]] ne "port:clk:0"} {error "BODY_CANARY native positive root mismatch $id"}
 dict set bc_members $id $name;dict set bc_stage $bit:$stage $name
}
close $f
if {[dict size $bc_members]!=12012} {error "BODY_CANARY incomplete91x132 cohort"}
set bc_edges {}
for {set bit 0} {$bit<132} {incr bit} {
 for {set stage 1} {$stage<=90} {incr stage} {
  set a [dict get $bc_stage $bit:[expr {$stage-1}]];set b [dict get $bc_stage $bit:$stage]
  if {![la_same_clock [list $a $b]] || $b ni [la_succ [[dict get $la_ck $a] getInst] 4]} {error "BODY_CANARY actual native edge mismatch $bit:$stage"}
  lappend bc_edges [list $a $b]
 }
}
puts "BODY_CANARY native_members12012 direct_edges[llength $bc_edges] master_clock_root_phase_dataPASS report_only1"
foreach profile {A30 B50} {
 set radius [expr {$profile eq "A30" ? 30.0 : 50.0}]
 set assignment {};dict for {name it} $la_ck {dict set assignment $name [[$it getNet] getName]}
 set groups {};set f [open [file join $bc_dir groups_$profile.tsv] r];gets $f header
 if {$header ne "group\ttarget_leaf\tinstance"} {error "BODY_CANARY bad group schema"}
 set moved {};set seen {}
 while {[gets $f line]>=0} {
  lassign [split $line "\t"] group leaf id
  if {![dict exists $bc_members $id] || [dict exists $seen $id]} {error "BODY_CANARY repeated/nonmetadata group member"}
  dict set seen $id 1;dict lappend groups $group [list $leaf [dict get $bc_members $id]]
 }
 close $f
 set loads $la_fo;set cap [expr {$la_fomax+4}]
 dict for {gid records} $groups {
  if {[llength $records]>24 || [llength $records]<2} {error "BODY_CANARY group bound"}
  set names {};set leafname [lindex [lindex $records 0] 0]
  foreach rec $records {if {[lindex $rec 0] ne $leafname} {error "BODY_CANARY mixedtarget"};lappend names [lindex $rec 1]}
  if {![la_same_clock $names]} {error "BODY_CANARY actual clock mismatch"}
  set leafinst [$la_blk findInst $leafname]
  if {$leafinst eq "NULL" || ![la_is_bufinv $leafinst]} {error "BODY_CANARY invalid leaf driver"}
  set target {};foreach it [$leafinst getITerms] {if {[$it isOutputSignal]} {set target [$it getNet];break}}
  if {$target eq {} || [$target getSigType] ne "CLOCK" || [la_groot $target] ne "port:clk:0"} {error "BODY_CANARY target gating/phase mismatch"}
  set tn [$target getName];lassign [la_xy $leafinst] dx dy
  foreach name $names {
   set it [dict get $la_ck $name];lassign [la_xy [$it getInst]] x y
   if {abs($x-$dx)+abs($y-$dy)>$radius*$la_dbu+0.01} {error "BODY_CANARY radius $profile $gid $name"}
   set old [dict get $assignment $name]
   if {$old ne $tn} {dict incr loads $old -1;dict incr loads $tn 1;dict set assignment $name $tn;dict set moved $name 1}
  }
  if {[dict get $loads $tn]>$cap} {error "BODY_CANARY actual fanout cap $profile $gid"}
 }
 foreach stage {0 90} {
  for {set bit 0} {$bit<132} {incr bit} {
   set name [dict get $bc_stage $bit:$stage]
   if {[dict get $assignment $name] ne [[la_leaf $name] getName]} {error "BODY_CANARY boundary clock anchor changed $profile $bit:$stage"}
  }
 }
 set changed_leaves {};dict for {name v} $moved {dict set changed_leaves [[la_leaf $name] getName] 1;dict set changed_leaves [dict get $assignment $name] 1}
 set affected_nonmeta 0;set af [open [file join $bc_dir affected_nonmetadata_$profile.tsv] w];puts $af "instance\toriginal_clock_net\told_sink_count\tnew_sink_count"
 dict for {name it} $la_ck {
  if {[dict exists $bc_members [bc_norm $name]]} {continue}
  set nn [[$it getNet] getName]
  if {[dict exists $changed_leaves $nn]} {incr affected_nonmeta;puts $af "$name\t$nn\t[dict get $la_fo $nn]\t[dict get $loads $nn]"}
 }
 close $af
 puts "BODY_CANARY profile=$profile boundary_anchors264PASS changed_leaf_nets=[dict size $changed_leaves] affected_nonmetadata_clock_members=$affected_nonmeta full_TT_FF_STA_REQUIRED"
 set oldcross 0;set newcross 0;set created 0
 foreach edge $bc_edges {
  lassign $edge a b;set old [expr {[la_leaf $a] ne [la_leaf $b]}];set new [expr {[dict get $assignment $a] ne [dict get $assignment $b]}]
  incr oldcross $old;incr newcross $new;if {!$old && $new} {incr created}
 }
 if {$created} {error "BODY_CANARY new original-coherent edge $profile"}
 # Quantify every actual zero-logic related edge outside the metadata chain.
 set nonmeta 0;set nonmeta_new 0;set nonmeta_removed 0
 foreach edge $la_pairlist {
  lassign $edge a b
  if {![dict exists $moved $a] && ![dict exists $moved $b]} {continue}
  if {[dict exists $bc_members [bc_norm $a]] && [dict exists $bc_members [bc_norm $b]]} {continue}
  incr nonmeta
  set old [expr {[la_leaf $a] ne [la_leaf $b]}];set new [expr {[dict get $assignment $a] ne [dict get $assignment $b]}]
  if {!$old && $new} {incr nonmeta_new};if {$old && !$new} {incr nonmeta_removed}
 }
 if {$nonmeta_new} {error "BODY_CANARY candidate creates nonmetadata edge crossings $profile $nonmeta_new"}
 puts "BODY_CANARY profile=$profile groups=[dict size $groups] moved=[dict size $moved] cap=$cap radius=$radius old_cross=$oldcross new_cross=$newcross new_native_cross=$created affected_nonmetadata_zero_logic=$nonmeta new_nonmetadata_cross=$nonmeta_new removed_nonmetadata_cross=$nonmeta_removed report_only=1"
}
puts "BODY_CANARY PASS no_clock_data_reset_master_or_pose_mutation"
