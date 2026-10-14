read_db /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_gate/base/3_5_place_dp-failed.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /probe/names.txt r]
while {[gets $f name]>=0} {
 set i [$b findInst $name]
 if {$i eq "NULL"} {puts "MISSING $name";continue}
 set bb [$i getBBox]
 puts "CELL $name [$i getPlacementStatus] [$i isFixed] [$i isDoNotTouch] [[$i getMaster] getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"
 foreach j [$b getInsts] {
  if {$j eq $i} continue
  set z [$j getBBox]
  if {[$bb xMin]<[$z xMax] && [$bb xMax]>[$z xMin] && [$bb yMin]<[$z yMax] && [$bb yMax]>[$z yMin]} {
   puts "OVERLAP $name [$j getName] [$j getPlacementStatus] [$j isFixed] [$j isDoNotTouch] [[$j getMaster] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]"
  }
 }
}
close $f
exit
