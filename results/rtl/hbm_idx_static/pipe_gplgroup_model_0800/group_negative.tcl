read_db /audit/model_group_gpl.odb
source /audit/group_complete.tcl
source /audit/validate_group.tcl
set block [ord::get_db_block]
set before [ot_idx_region_signature]
set mode $::idx_negative_mode
if {$mode eq "missing"} {
 odb::dbGroup_destroy [$block findGroup codex_idx_lower_group]
} elseif {$mode eq "outside"} {
 set target NULL
 foreach i [$block getInsts] {
  if {[$i getGroup] eq "NULL" || [$i isDoNotTouch] || [$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  set target $i;break
 }
 if {$target eq "NULL"} {error NEGATIVE_FIXTURE_NO_MOVABLE_CELL}
 set u [[ord::get_db_tech] getDbUnitsPerMicron]
 $target setOrigin [expr {round(20*$u)}] [expr {round(86.4*$u)}]
 puts "NEGATIVE_MOVED_ACTUAL_CELL [$target getName]"
} elseif {$mode ne "positive"} {error UNKNOWN_MODE}
if {$before ne [ot_idx_region_signature]} {error NEGATIVE_FIXTURE_CHANGED_GRAPH_PG_DNT}
puts NEGATIVE_FIXTURE_GRAPH_PG_DNT_IDENTITY_PASS
ot_idx_validate_consumed_group
