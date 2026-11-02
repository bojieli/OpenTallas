# Strictly shorter failure discriminator: no repair, route, legalize or STA.
source /work/pg_birth/native_pg_binding.tcl
source /work/clk_freeze.tcl
set b [ord::get_db_block]
ot_pg_assert_all_native $b [ot_pg_prepare $b]
ot_pg_audit_snapshot $b /work/FRESH_PA_INPUT_PG.json
ot_clk_dump /work/FRESH_PA_CLOCK_INPUT.tsv fresh_pa_input
proc pa_structure {b} {
 set cells {};set nets {};set terms {}
 foreach i [$b getInsts] {
  set ts {};foreach t [$i getITerms] {set n [$t getNet];lappend ts [list [[$t getMTerm] getName] $n]}
  lappend cells [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [lsort $ts]]
 }
 foreach n [$b getNets] {lappend nets [list [$n getName] [$n getSigType] [$n isSpecial] [$n isDoNotTouch]]}
 foreach t [$b getBTerms] {lappend terms [list [$t getName] [$t getNet] [$t getSigType] [$t getIoType]]}
 return [list [lsort $cells] [lsort $nets] [lsort $terms]]
}
set before [pa_structure $b]
proc pa_catalog {b path} {
 set f [open $path {WRONLY CREAT EXCL}]
 puts $f "BLOCK_AP [llength [$b getAccessPoints]]"
 foreach name {wire19103 wire19104 wire19105} {
  set i [$b findInst $name];if {$i eq "NULL"} {error "MISSING_ACTUAL_AFTER_DRV_BUFFER $name"}
  set m [$i getMaster];set idx [$i getPinAccessIdx]
  lassign [$i getLocation] ix iy
  set box [$i getBBox]
  puts $f [list INST $name [$m getName] $idx $ix $iy origin [$i getOrigin] bbox [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] [$i getOrient] [$i getPlacementStatus]]
  foreach mt [$m getMTerms] {
   if {[$mt getSigType] in {POWER GROUND}} continue
   foreach mp [$mt getMPins] {
    set buckets [$mp getPinAccess]
    puts $f [list MPIN [$mt getName] [$mp getId] bucket_count [llength $buckets] selected_idx $idx selected_slot_count [llength [lindex $buckets $idx]]]
    foreach ap [lindex $buckets $idx] {puts $f [list ACCESS_POINT [$ap getId] owner_mpin [[$ap getMPin] getId]]}
   }
  }
  foreach r [$b getRows] {
   lassign [$r getOrigin] rx ry;set site [$r getSite]
   set pitch [$r getSpacing];if {$pitch<=0} {set pitch [$site getWidth]}
   if {$iy == $ry && $ix >= $rx && $ix < $rx+[$r getSiteCount]*$pitch} {
    puts $f [list ROW [$r getName] $rx $ry [$r getOrient] pitch $pitch site_width [$site getWidth] site_height [$site getHeight] x_remainder [expr {($ix-$rx)%$pitch}] master_width [$m getWidth] master_height [$m getHeight]]
   }
  }
  foreach other [$b getInsts] {
   if {$other eq $i} continue
   set ob [$other getBBox]
   if {max([$box xMin],[$ob xMin]) < min([$box xMax],[$ob xMax]) && max([$box yMin],[$ob yMin]) < min([$box yMax],[$ob yMax])} {
    puts $f [list OVERLAP [$other getName] [[$other getMaster] getName] [[$other getMaster] getType] [list [$ob xMin] [$ob yMin] [$ob xMax] [$ob yMax]]]
   }
  }
 }
 close $f
}
pa_catalog $b /work/FRESH_PA_BEFORE.tsv
proc pa_forbidden {args} {error FRESH_PA_NO_REPAIR_NO_ROUTE_NO_CELL_BIRTH}
foreach cmd {repair_design repair_timing clock_tree_synthesis buffer_ports repair_clock_inverters global_placement detailed_placement global_route detailed_route repair_antennas} {
 if {[info commands $cmd] ne ""} {trace add execution ::$cmd enter ::pa_forbidden}
}
set_routing_layers -signal M2-M5 -clock M2-M5
pin_access
pa_catalog $b /work/FRESH_PA_AFTER.tsv
if {[pa_structure $b] ne $before} {error FRESH_PA_DATA_CLOCK_MASTER_POSE_STATUS_NETFLAG_MUTATION}
ot_pg_assert_all_native $b [ot_pg_prepare $b]
ot_pg_audit_snapshot $b /work/FRESH_PA_AFTER_PG.json
ot_clk_dump /work/FRESH_PA_CLOCK_AFTER.tsv fresh_pa_after
set f [open /work/FRESH_PA_RESULT.json {WRONLY CREAT EXCL}]
puts $f {{"kind":"FRESH_PROCESS_PIN_ACCESS_ONLY","status":"PASS","repair_executed":false,"setup_executed":false,"route_executed":false,"sta_credit":false,"qualified_grt":false}}
close $f
exit 0
