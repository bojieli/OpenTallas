read_db /work/results/asap7/opentallas_ot_hgi_b2_dma_rq_asap7_ref_gate/base/3_place.odb
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set rows [dict create]
set occ [dict create]
foreach r [$b getRows] {
 set rb [$r getBBox]; set y [$rb yMin]; set rh [[$r getSite] getHeight];set sw [[$r getSite] getWidth]
 dict lappend rows $y [list [$rb xMin] [$rb xMax]]
}
set cw [[[ord::get_db] findMaster BUFx24_ASAP7_75t_R] getWidth]
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]||![$i isPlaced]} {continue}
 set bb [$i getBBox]
 for {set y [$bb yMin]} {$y<[$bb yMax]} {incr y $rh} {dict lappend occ $y [list [$bb xMin] [$bb xMax]]}
}
set total 0;set used 0;set contiguous 0;set optimistic 0;set runs 0;set largest 0
foreach y [dict keys $rows] {
 set intervals {};if {[dict exists $occ $y]} {set intervals [lsort -integer -index 0 [dict get $occ $y]]}
 foreach seg [dict get $rows $y] {
  lassign $seg x0 x1;incr total [expr {$x1-$x0}];set at $x0
  foreach v $intervals {
   lassign $v a z;if {$z<=$x0||$a>=$x1} {continue}
   set a [expr {max($a,$x0)}];set z [expr {min($z,$x1)}]
   if {$a>$at} {set gap [expr {$a-$at}];incr contiguous [expr {$gap/($cw+2*$sw)}];incr optimistic [expr {($gap+2*$sw)/($cw+2*$sw)}];incr runs;if {$gap>$largest} {set largest $gap}}
   if {$z>$at} {incr used [expr {$z-max($at,$a)}];set at $z}
  }
  if {$at<$x1} {set gap [expr {$x1-$at}];incr contiguous [expr {$gap/($cw+2*$sw)}];incr optimistic [expr {($gap+2*$sw)/($cw+2*$sw)}];incr runs;if {$gap>$largest} {set largest $gap}}
 }
}
set bins [dict create];set ns 0;set bin [expr {60*$dbu}]
set n [[[$b findBTerm clk] getNet] getITerms]
foreach it $n {
 if {[$it getIoType] ne "INPUT"} {continue}
 lassign [$it getAvgXY] ok x y
 if {!$ok} {lassign [[$it getInst] getLocation] x y}
 set key "[expr {int($x/$bin)}],[expr {int($y/$bin)}]";dict incr bins $key;incr ns
}
set nl 0;dict for {k count} $bins {incr nl [expr {($count+7)/8}]}
puts "RQ_SPINE sinks=$ns bins=[dict size $bins] leaves=$nl minimum_initial_tree_buffers=[expr {2*$nl-1}] optimistic_disjoint_free_clock_footprints=$optimistic"
puts "RQ_FREE total_row_width_dbu=$total used_row_width_dbu=$used free_pct=[expr {100.0*($total-$used)/$total}] clock_buffer_width_um=[expr {double($cw)/$dbu}] disjoint_clock_footprints_with_gap=$contiguous gap_runs=$runs largest_gap_um=[expr {double($largest)/$dbu}]"
exit
