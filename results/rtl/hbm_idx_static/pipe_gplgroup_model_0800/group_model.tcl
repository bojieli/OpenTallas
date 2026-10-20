set ods [glob /job/routes/gate/work/orfs/results/asap7/*/base/3_place.odb]
if {[llength $ods]!=1} {error "ambiguous checkpoint"}
read_db [lindex $ods 0]
source /audit/native_pg_binding.tcl
set block [ord::get_db_block]
set bound [ot_pg_bind_batch_before_protect $block [$block getInsts]]
puts "MODEL_CANONICAL_EXISTING_RULES_BIND $bound"
source /audit/group_complete.tcl
# Private model fixture uses the already priced new43.2um band, not the old37.8um one.
set before [ot_idx_region_signature]
set r [$block findRegion codex_idx_lower_band]
odb::dbRegion_destroy $r
ot_idx_region_refresh model_group_creation
if {$before ne [ot_idx_region_signature]} {error MODEL_GRAPH_CHANGED}
ot_idx_region_refresh model_group_idempotence
set grp [$block findGroup codex_idx_lower_group]
set count 0
foreach i [$block getInsts] {if {[$i getGroup] eq $grp} {incr count}}
puts "ACTUAL_GROUP_MEMBERS $count region=[[$grp getRegion] getName]"
if {$count!=46554 || $::ot_idx_region_unbound_stage!=0} {error MODEL_GROUP_CENSUS_FAILED}
write_db /audit/model_group_input.odb
puts IDX_GROUP_METADATA_MODEL_PASS
