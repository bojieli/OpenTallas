# A0-REPACK 10-23 (gen_repack.py): tools/qwen_romleaf/rc15_2000/local_request_decode.tcl with the decoder boxes
# on the re-packed ROM pin lanes, and the leaf lookup fixed: reset_landing wraps the soft logic in u_ot_pr_core.
# but the hard leaves keep their names, and odb names carry backslash escapes (rc15a GPL hook FAIL 'no matching
# hard leaf').  Nothing else changed.
# Private combinational request decoders in the existing free macro gutters.
# Source state, source/capture clock entries, hard children and edges are unchanged.
# qrl_* reservations are released by the existing rc14 hook before DPL.
set qr15_block [ord::get_db_block]
set qr15_dbu [$qr15_block getDbUnitsPerMicron]
set qr15_members [dict create]
foreach inst [$qr15_block getInsts] {
 set name [string map [list "\\" ""] [$inst getName]]
 if {![regexp {^(.*g_rph\.g_rb\[([0-9]+)\]\.g_single\.g_col\[([01])\])\.u_req_any[/.]} $name -> scope bank col]} {continue}
 if {[[$inst getMaster] isSequential] || [[$inst getMaster] isBlock]} {error "A0 local request decoder unexpectedly contains state or macro: $name"}
 dict lappend qr15_members $scope $inst
}
if {[dict size $qr15_members] != 10} {error "A0 local request decoders: expected 10 physical leaves, found [dict size $qr15_members]"}
foreach scope [dict keys $qr15_members] {
 set leaf NULL
 regsub {^u_ot_pr_core\.} $scope {} qr15_lscope
 foreach qr15_c [$qr15_block getInsts] {if {[[$qr15_c getMaster] isBlock] && [string map [list "\\" ""] [$qr15_c getName]] in [list "${qr15_lscope}.u_leaf" "${scope}.u_leaf"]} {set leaf $qr15_c;break}}
 if {$leaf eq "NULL" || $leaf eq ""} {error "A0 request decoder has no matching hard leaf: $scope"}
 set bb [$leaf getBBox]
 regexp {g_rb\[([0-9]+)\]\.g_single\.g_col\[([01])\]$} $scope -> bank col
 # ROM any_d is at local y=21.564 um; MY changes X only.
 set cy [expr {[$bb yMin]/double($qr15_dbu)+21.564}]
 if {$col==0} {set x0 45.160;set x1 50.560} else {set x0 407.360;set x1 412.760}
 set y0 [expr {$cy-2.7}];set y1 [expr {$cy+2.7}]
 set capacity 0.0
 foreach row [$qr15_block getRows] {
  set r [$row getBBox]
  set capacity [expr {$capacity+max(0.0,min($x1,[$r xMax]/double($qr15_dbu))-max($x0,[$r xMin]/double($qr15_dbu)))*max(0.0,min($y1,[$r yMax]/double($qr15_dbu))-max($y0,[$r yMin]/double($qr15_dbu)))}]
 }
 set members [dict get $qr15_members $scope];set area 0.0
 foreach inst $members {set m [$inst getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/($qr15_dbu*$qr15_dbu)}]}
 if {[llength $members]<1 || [llength $members]>8 || $capacity<=0 || $area/$capacity>0.25} {error "A0 request decoder lacks row margin: bank=$bank col=$col cells=[llength $members] area=$area capacity=$capacity"}
 set name qrl_reqany_b${bank}c${col}
 set region [odb::dbRegion_create $qr15_block $name]
 $region setRegionType EXCLUSIVE
 odb::dbBox_create $region [expr {round($x0*$qr15_dbu)}] [expr {round($y0*$qr15_dbu)}] [expr {round($x1*$qr15_dbu)}] [expr {round($y1*$qr15_dbu)}]
 set group [odb::dbGroup_create $region $name]
 foreach inst $members {$group addInst $inst}
 puts "A0_LOCAL_REQUEST_DECODE bank=$bank col=$col cells=[llength $members] area=$area capacity=$capacity box=$x0,$y0,$x1,$y1"
}
puts "A0_LOCAL_REQUEST_DECODE_PASS leaves=[dict size $qr15_members] state_added=0 edges_added=0"
