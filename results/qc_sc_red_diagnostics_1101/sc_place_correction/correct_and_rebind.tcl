# One approved source-event diagnostic: import actual PLACE and rebind only
# selected internal FF poses and existing DFF CLK pins to the model's existing fixed same-depth leaf drivers.
# No synthesis, optimization, CTS, STA, parasitic extraction, global or detailed routing.
read_db /work/input.odb
set b [ord::get_db_block]
set units [expr {double([$b getDbUnitsPerMicron])}]
proc need {ok msg} {if {!$ok} {error $msg}}
proc cell_state {b} {
 set out {};foreach i [$b getInsts] {dict set out [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]};return $out
}
proc incidence {b} {
 set out {};foreach i [$b getInsts] {foreach t [$i getITerms] {set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};dict set out [list [$i getName] [[$t getMTerm] getName]] $nn}};return $out
}
proc terms {b} {set out {};foreach p [$b getBTerms] {set n [$p getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};dict set out [$p getName] [list [$p getIoType] [$p getSigType] $nn]};return $out}
proc nets {b} {set out {};foreach n [$b getNets] {dict set out [$n getName] [list [$n getSigType] [$n isSpecial] [$n isDoNotTouch]]};return $out}
set before_cells [cell_state $b];set before_inc [incidence $b];set before_terms [terms $b];set before_nets [nets $b]
set fh [open /work/node_names.list];set nodes [split [string trim [read $fh]] \n];close $fh
need [expr {[llength $nodes]==2389}] {node count}
foreach node_row $nodes {
 lassign [split $node_row \t] name parent

 set i [$b findInst $name]
 need [expr {$i ne "NULL" && [[$i getMaster] getName] eq "BUFx24_ASAP7_75t_R" && [$i getPlacementStatus] eq "FIRM"}] "fixed node identity $name"
 set a [$i findITerm A]
 if {$parent eq "port:ck"} {set expected_input [[$b findBTerm ck] getNet]} else {set expected_input [[[$b findInst $parent] findITerm Y] getNet]}
 need [expr {$a ne "NULL" && [$a getNet] eq $expected_input}] "native clock parent mismatch $name $parent"
}
# Exact boundedPLACE-only correction: actual individual widths and full oldbody/TAP legality were reviewed.
set row_orient {};foreach r [$b getRows] {dict set row_orient [lindex [$r getOrigin] 1] [$r getOrient]}
set fh [open /work/moves.tsv];set move_rows [split [string trim [read $fh]] \n];close $fh
set expected_cells $before_cells
foreach row $move_rows {
 lassign [split $row \t] name master ox oy nx ny width height
 set i [$b findInst $name];need [expr {$i ne "NULL" && [[$i getMaster] getName] eq $master && [string match DFF* $master]}] "pose sink identity $name"
 set oldbb [$i getBBox];need [expr {[$oldbb xMin]==$ox && [$oldbb yMin]==$oy && ([$oldbb xMax]-[$oldbb xMin])==$width && ([$oldbb yMax]-[$oldbb yMin])==$height}] "old bbox/master-size mismatch $name"
 need [dict exists $row_orient $ny] "missing row $name $ny"
 set flag [$i isDoNotTouch];if {$flag} {$i setDoNotTouch 0}
 try {$i setOrient [dict get $row_orient $ny];$i setLocation $nx $ny} finally {$i setDoNotTouch $flag}
 set bb [$i getBBox];need [expr {[$bb xMin]==$nx && [$bb yMin]==$ny && ([$bb xMax]-[$bb xMin])==$width && ([$bb yMax]-[$bb yMin])==$height}] "target bbox mismatch $name"
 dict set expected_cells $name [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
}
check_placement -verbose
set fh [open /work/assignment.tsv];set rows [split [string trim [read $fh]] \n];close $fh
need [expr {[llength $rows]==42665}] {assignment count}
set expected $before_inc;set changed 0;set seen {};set leaf_counts {};set max_reach 0.0
foreach row $rows {
 lassign [split $row \t] name port leaf oldleaf master
 need [expr {![dict exists $seen $name]}] "duplicate DFF $name";dict set seen $name 1
 set i [$b findInst $name];set li [$b findInst $leaf]
 need [expr {$i ne "NULL" && [[$i getMaster] getName] eq $master && [string match DFF* $master] && $port eq "CLK"}] "sink identity $name"
 need [expr {$li ne "NULL" && [[$li getMaster] getName] eq "BUFx24_ASAP7_75t_R" && [$li getPlacementStatus] eq "FIRM"}] "leaf identity $leaf"
 set pin [$i findITerm CLK];set yp [$li findITerm Y]
 need [expr {$pin ne "NULL" && $yp ne "NULL" && [$pin getNet] ne "NULL" && $yp ne "NULL" && [$pin getNet] eq [[[$b findInst $oldleaf] findITerm Y] getNet]}] "original native CLK mismatch $name"
 set net [$yp getNet];need [expr {$net ne "NULL"}] "leaf output missing $leaf"
 set ar [$pin getBBox];set yr [$yp getBBox]
 set dist [expr {(abs(([$ar xMin]+[$ar xMax])-([$yr xMin]+[$yr xMax]))+abs(([$ar yMin]+[$ar yMax])-([$yr yMin]+[$yr yMax])))/(2*$units)}]
 
 set max_reach [expr {max($max_reach,$dist)}]
 if {[$pin getNet] ne $net} {
  # These exact nodes/nets were frozen by the native pre-CTS plan. The
  # authorized source rebind temporarily unlocks only this explicit edge;
  # every flag is restored even if an OpenDB mutation raises an exception.
  set protected {}
  foreach obj [list $i [$pin getNet] $net] {
   dict set protected $obj [$obj isDoNotTouch]
   if {[$obj isDoNotTouch]} {$obj setDoNotTouch 0}
  }
  try {$pin disconnect;$pin connect $net;incr changed} finally {
   dict for {obj flag} $protected {$obj setDoNotTouch $flag}
  }
 }
 dict incr leaf_counts $leaf
 dict set expected [list $name CLK] [$net getName]
}
need [expr {[dict size $seen]==42665 && [dict size $leaf_counts]==1024}] {coverage count}
set actual_dff 0;foreach i [$b getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {incr actual_dff;need [expr {[dict exists $seen [$i getName]]}] "unassigned native DFF [$i getName]"}}
need [expr {$actual_dff==42665}] {native DFF total}
dict for {leaf count} $leaf_counts {need [expr {$count>=1 && $count<=42}] "leaf load $leaf $count"}
need [expr {[cell_state $b] eq $expected_cells}] {unexpected cell/master/pose/status mutation}
need [expr {[incidence $b] eq $expected}] {non-CLK or unexpected connectivity mutation}
need [expr {[terms $b] eq $before_terms}] {BTerm mutation}
need [expr {[nets $b] eq $before_nets}] {net identity/class/special mutation}
set f [open /work/rebind_summary.json w]
puts $f [format {{"scope":"BOUNDED_PLACE_CORRECTION_AND_REBIND_NO_CTS_STA_GRT","verdict":"PASS","native_DFFs":42665,"fixed_clock_nodes":2389,"leaf_drivers":1024,"changed_CLK_connections":%d,"max_actual_Y_to_CLK_L1_um":%.9f,"leaf_cap":42,"all_original_masters_nonselected_poses_nonCLK_connections_preserved":true,"parent_absolute_frame_qualified":false,"cycles_added":0}} $changed $max_reach]
close $f
# Standard native supply binding; data/clockgraph guards above stay independent.
source /work/pg_connect.tcl
ot_pg_connect_all sc_place_corrected
ot_pg_require_bound sc_place_corrected
set ::env(OT_GEOM_OUT) /work/sc_actual_corrected.tsv
source /work/geom_dump.tcl
source /work/sc_guard.tcl
set f [open /work/sc_guard_state.tcl w]
foreach {name val} [list sc_expected_cells [sc_cells] sc_expected_inc [sc_inc] sc_expected_terms [sc_terms] sc_expected_nets [sc_nets]] {puts $f [list set ::$name $val]}
close $f
write_db /work/sc_place_corrected.odb
puts "SC_CORRECTION_REBIND_COMPLETE changed=$changed max_actual_Y_to_CLK_L1_um=$max_reach no_CTS_STA_GRT"
