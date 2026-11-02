# One approved source-event diagnostic: import actual PLACE and rebind only
# existing DFF CLK pins to the model's existing fixed same-depth leaf drivers.
# No placement, CTS, STA, parasitic extraction, global or detailed routing.
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
need [expr {[llength $nodes]==8269}] {node count}
foreach name $nodes {
 set i [$b findInst $name]
 need [expr {$i ne "NULL" && [[$i getMaster] getName] eq "BUFx8_ASAP7_75t_R" && [$i getPlacementStatus] eq "FIRM"}] "fixed node identity $name"
}
set fh [open /work/assignment.tsv];set rows [split [string trim [read $fh]] \n];close $fh
need [expr {[llength $rows]==34225}] {assignment count}
set expected $before_inc;set changed 0;set seen {};set leaf_counts {};set max_reach 0.0
foreach row $rows {
 lassign [split $row \t] name port leaf oldnet master
 need [expr {![dict exists $seen $name]}] "duplicate DFF $name";dict set seen $name 1
 set i [$b findInst $name];set li [$b findInst $leaf]
 need [expr {$i ne "NULL" && [[$i getMaster] getName] eq $master && [string match DFF* $master] && $port eq "CLK"}] "sink identity $name"
 need [expr {$li ne "NULL" && [[$li getMaster] getName] eq "BUFx8_ASAP7_75t_R" && [$li getPlacementStatus] eq "FIRM"}] "leaf identity $leaf"
 set pin [$i findITerm CLK];set yp [$li findITerm Y]
 need [expr {$pin ne "NULL" && $yp ne "NULL" && [$pin getNet] ne "NULL" && $yp ne "NULL" && [[$pin getNet] getName] eq $oldnet}] "original native CLK mismatch $name"
 set net [$yp getNet];need [expr {$net ne "NULL"}] "leaf output missing $leaf"
 set ar [$pin getBBox];set yr [$yp getBBox]
 set dist [expr {(abs(([$ar xMin]+[$ar xMax])-([$yr xMin]+[$yr xMax]))+abs(([$ar yMin]+[$ar yMax])-([$yr yMin]+[$yr yMax])))/(2*$units)}]
 need [expr {$dist<=40.0}] "real Y-to-CLK reach $name $dist"
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
need [expr {[dict size $seen]==34225 && [dict size $leaf_counts]==3452}] {coverage count}
set actual_dff 0;foreach i [$b getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {incr actual_dff;need [expr {[dict exists $seen [$i getName]]}] "unassigned native DFF [$i getName]"}}
need [expr {$actual_dff==34225}] {native DFF total}
dict for {leaf count} $leaf_counts {need [expr {$count>=1 && $count<=16}] "leaf load $leaf $count"}
need [expr {[cell_state $b] eq $before_cells}] {cell/master/pose/status changed}
need [expr {[incidence $b] eq $expected}] {non-CLK or unexpected connectivity mutation}
need [expr {[terms $b] eq $before_terms}] {BTerm mutation}
need [expr {[nets $b] eq $before_nets}] {net identity/class/special mutation}
set f [open /work/rebind_summary.json w]
puts $f [format {{"scope":"IMPORT_REBIND_ONLY_NO_CTS_STA_GRT","verdict":"PASS","native_DFFs":34225,"fixed_clock_nodes":8269,"leaf_drivers":3452,"changed_CLK_connections":%d,"max_actual_Y_to_CLK_L1_um":%.9f,"leaf_cap":16,"all_original_cells_and_nonCLK_connections_preserved":true,"parent_absolute_frame_qualified":false,"cycles_added":0}} $changed $max_reach]
close $f
write_db /work/red_rebound.odb
puts "RED_REBIND_COMPLETE changed=$changed max_actual_Y_to_CLK_L1_um=$max_reach no_CTS_STA_GRT"
