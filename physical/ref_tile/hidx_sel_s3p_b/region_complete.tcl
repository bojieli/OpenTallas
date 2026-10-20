# Private IDX source placement constraint. Never edits a net, PG binding or DNT flag.
if {![llength [info commands ord::get_db_block]]} {return}
proc ot_idx_region_signature {} {
 set b [ord::get_db_block];set sig {};set unbound 0
 foreach i [$b getInsts] {
  lappend sig [list I [$i getName] [[$i getMaster] getName] [$i isDoNotTouch]]
  foreach p [$i getITerms] {
   set n [$p getNet];set name NULL
   if {$n ne "NULL"} {set name [$n getName]}
   if {$n eq "NULL" && [[$p getMTerm] getSigType] in {POWER GROUND}} {incr unbound}
   lappend sig [list P [$i getName] [[$p getMTerm] getName] $name]
  }
 }
 foreach p [$b getBTerms] {
  set n [$p getNet];set name NULL
  if {$n ne "NULL"} {set name [$n getName]}
  lappend sig [list B [$p getName] [$p getIoType] [$p getSigType] $name]
 }
 foreach n [$b getNets] {lappend sig [list N [$n getName] [$n getSigType] [$n isDoNotTouch]]}
 set ::ot_idx_region_unbound_stage $unbound
 return $sig
}
proc ot_idx_region_refresh {stage} {
 set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 set before [ot_idx_region_signature]
 set r [$b findRegion codex_idx_lower_band]
 if {$r eq "NULL"} {
  set r [odb::dbRegion_create $b codex_idx_lower_band]
  $r setRegionType EXCLUSIVE
  odb::dbBox_create $r [expr {round(2.16*$dbu)}] [expr {round(2.16*$dbu)}] [expr {round(343.44*$dbu)}] [expr {round(45.36*$dbu)}]
 }
 set added 0;set total 0;set area 0.0
 foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} continue
  set functional 0
  foreach p [$m getMTerms] {if {[$p getSigType] ni {POWER GROUND}} {set functional 1;break}}
  if {!$functional} continue
  incr total
  set area [expr {$area+double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
  set old [$i getRegion]
  if {$old eq "NULL" || [$old getId] != [$r getId]} {incr added;$r addInst $i}
  set now [$i getRegion]
  if {$now eq "NULL" || [$now getId] != [$r getId]} {error "IDX_REGION_MISSING [$i getName]"}
 }
 if {$before ne [ot_idx_region_signature]} {error "IDX_REGION_CHANGED_GRAPH_PG_OR_DNT"}
 puts "IDX_REGION_COMPLETE stage=$stage functional=$total added=$added actual_area_um2=$area PG_bindings_preserved=PASS unbound_stage=$::ot_idx_region_unbound_stage graph_DNT_identity=PASS"
}
if {![llength [info commands ::ot_idx_original_detailed_placement]] && [llength [info commands detailed_placement]]} {
 rename detailed_placement ::ot_idx_original_detailed_placement
 proc detailed_placement {args} {
  ot_idx_region_refresh before_detailed_placement
  if {[catch {uplevel 1 [list ::ot_idx_original_detailed_placement {*}$args]} value options]} {
   # Keep the actual failing state; no earlier original checkpoint is overwritten.
   if {[file isdirectory /work/results]} {write_db /work/idx_failed_dpl_checkpoint.odb}
   return -options $options $value
  }
  ot_idx_region_refresh after_detailed_placement
  return $value
 }
}
