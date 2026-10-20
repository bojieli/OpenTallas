set ods [glob /job/routes/gate/work/orfs/results/asap7/*/base/3_place.odb]
if {[llength $ods]!=1} {error "ambiguous checkpoint"}
read_db [lindex $ods 0]
source /audit/native_pg_binding.tcl
set block [ord::get_db_block]
# MODEL SETUP ONLY: canonical existing-rule birth bind on private in-memory copy.
set bound [ot_pg_bind_batch_before_protect $block [$block getInsts]]
puts "MODEL_CANONICAL_EXISTING_RULES_BIND $bound"
source /audit/region_complete.tcl
ot_idx_region_refresh model_before_dpl
ot_idx_region_refresh model_idempotence
write_db /audit/model_region_updated.odb
if {$::ot_idx_region_unbound_stage != 0} {error "MODEL_FINAL_PG_NOT_ZERO"}
puts IDX_REGION_MODEL_PASS
