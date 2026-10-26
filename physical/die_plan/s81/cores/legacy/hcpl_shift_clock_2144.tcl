# HCPL structural clock recipe: one local clock group for each full u_d4 delay chain.
# PRE_CTS only, after a placed original netlist. No data/RTL cells or cycles change.
# Calls the shared zero-logic graph census in report-only mode, then keeps each
# complete <=24-register chain on a dedicated BUFx24 root. All ordinary/reset
# clock sinks stay explicitly inventoried on the original clock root.
# OT_HCPL_SHIFT_PLAN_ONLY=1 emits the proposed ownership without mutating the DB.
uplevel #0 {
set ::env(OT_LEAF_AFF_REPORT_ONLY) 1
source /work/leaf_affinity.tcl
unset ::env(OT_LEAF_AFF_REPORT_ONLY)
set hs_blk [ord::get_db_block]
set hs_u [$hs_blk getDbUnitsPerMicron]
set hs_root [[$hs_blk findBTerm clk] getNet]
if {$hs_root eq "NULL"} {error "HCPL_SHIFT missing root clk"}
set hs_groups {};set hs_used [dict create];set hs_line 0
set hs_all [dict keys $la_ck]
dict for {r mem} $la_groups {
 set selected 0
 foreach n $mem {if {[string first {u_core.u_d4.genblk1.g_line.line} $n]>=0} {set selected 1;break}}
 if {!$selected} continue
 if {[llength $mem]>24 || ![la_same_clock $mem]} {error "HCPL_SHIFT invalid chain $r size [llength $mem]"}
 set sx 0.0;set sy 0.0;set n 0
 foreach name $mem {
  if {[dict exists $hs_used $name]} {error "HCPL_SHIFT duplicate sink $name"}
  set it [dict get $la_ck $name]
  if {[$it getNet] ne $hs_root} {error "HCPL_SHIFT preCTS only: $name not on root"}
  lassign [la_xy [$it getInst]] x y
  set sx [expr {$sx+$x}];set sy [expr {$sy+$y}];incr n
  if {[string first {u_core.u_d4.genblk1.g_line.line} $name]>=0} {incr hs_line}
 }
 set cx [expr {$sx/$n}];set cy [expr {$sy/$n}]
 set md 0.0
 foreach name $mem {lassign [la_xy [[dict get $la_ck $name] getInst]] x y;set d [expr {(abs($x-$cx)+abs($y-$cy))/double($hs_u)}];if {$d>$md} {set md $d}}
 if {$md>40} {error "HCPL_SHIFT chain spans $md um >40; re-place source chain first"}
 set k [llength $hs_groups]
 foreach name $mem {dict set hs_used $name $k}
 lappend hs_groups [list $cx $cy $mem]
}
if {[llength $hs_groups]!=32 || $hs_line!=608} {error "HCPL_SHIFT inventory changed: [llength $hs_groups] groups $hs_line line FF; expect32/608"}
set hs_fh [open /work/shift_clock_groups.tsv w]
puts $hs_fh "group\tname\tx_um\ty_um\tclock_owner\tcontrol"
set hs_reset 0;set hs_k 0
foreach G $hs_groups {
 lassign $G cx cy mem
 puts "HCPL_SHIFT group $hs_k sinks [llength $mem] planned_at [expr {$cx/$hs_u}] [expr {$cy/$hs_u}]"
 foreach name $mem {set it [dict get $la_ck $name];lassign [la_xy [$it getInst]] x y;puts $hs_fh "$hs_k\t$name\t[expr {$x/double($hs_u)}]\t[expr {$y/double($hs_u)}]\tshift_$hs_k\t0"}
 incr hs_k
}
foreach name $hs_all {
 if {[dict exists $hs_used $name]} continue
 set it [dict get $la_ck $name]
 if {[$it getNet] ne $hs_root} {error "HCPL_SHIFT unclaimed non-root clock $name"}
 set control [expr {[regexp {rst|reset|sync|valid|fault|ready|vo\$} $name]?1:0}]
 incr hs_reset $control
 lassign [la_xy [$it getInst]] x y
 puts $hs_fh "-1\t$name\t[expr {$x/double($hs_u)}]\t[expr {$y/double($hs_u)}]\tordinary\t$control"
}
close $hs_fh
puts "HCPL_SHIFT CENSUS all [llength $hs_all] grouped [dict size $hs_used] ordinary [expr {[llength $hs_all]-[dict size $hs_used]}] ordinary_control $hs_reset"
set hs_plan [expr {[info exists ::env(OT_HCPL_SHIFT_PLAN_ONLY)]?$::env(OT_HCPL_SHIFT_PLAN_ONLY):0}]
if {!$hs_plan} {
 set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
 if {$master eq "NULL"} {error "HCPL_SHIFT missing clock buffer"}
 set k 0
 foreach G $hs_groups {
  lassign $G cx cy mem
  set inst [odb::dbInst_create $hs_blk $master "hcpl_shift_tap_$k"]
  $inst setLocation [expr {int($cx)}] [expr {int($cy)}]
  $inst setPlacementStatus PLACED
  set net [odb::dbNet_create $hs_blk "hcpl_shift_net_$k"]
  $net setSigType CLOCK
  [$inst findITerm A] connect $hs_root
  [$inst findITerm Y] connect $net
  foreach it [$inst getITerms] {
   set mt [$it getMTerm]
   if {[$mt getSigType] in {POWER GROUND}} {set sn [$hs_blk findNet [$mt getName]];if {$sn eq "NULL"} {error "HCPL_SHIFT missing supply [$mt getName]"};$it connect $sn}
  }
  foreach name $mem {set it [dict get $la_ck $name];$it disconnect;$it connect $net}
  incr k
 }
 detailed_placement
 check_placement -verbose
 puts "HCPL_SHIFT BUILT32 clock roots, data path unchanged"
}
}
