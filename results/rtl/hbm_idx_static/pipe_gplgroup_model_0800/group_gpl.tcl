foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] {read_liberty $l}
read_liberty /job/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_tt.lib
read_db /audit/model_group_input.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
source /audit/group_complete.tcl
set block [ord::get_db_block]
set grp [$block findGroup codex_idx_lower_group]
set region [$block findRegion codex_idx_lower_band]
if {[$grp getRegion] ne $region} {error GPL_GROUP_REGION_MISMATCH}
set before [ot_idx_region_signature]
# Standard source density0.50; no region mask, inflation knob or timing repair.
global_placement -skip_initial_place -density 0.50 -overflow 0.10
if {$before ne [ot_idx_region_signature]} {error GPL_MODEL_CHANGED_GRAPH_PG_OR_DNT}
set n 0;set outside 0;set fixedoutside 0
set u [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
foreach i [$block getInsts] {
 if {[$i getGroup] ne $grp} continue
 incr n
 set bb [$i getBBox]
 if {[$bb xMin] < 2.16*$u-1 || [$bb yMin] < 2.16*$u-1 || [$bb xMax] > 343.44*$u+1 || [$bb yMax] > 45.36*$u+1} {
  incr outside
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {incr fixedoutside}
  if {$outside<=8} {puts "GPL_GROUP_OUTSIDE [$i getName] bbox=[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax] status=[$i getPlacementStatus]"}
 }
}
puts "ACTUAL_GPL_GROUP_RESULT group=[$grp getName] region=[[$grp getRegion] getName] members=$n outside=$outside fixedoutside=$fixedoutside PG_unbound=$::ot_idx_region_unbound_stage graph_DNT_identity=PASS"
write_db /audit/model_group_gpl.odb
if {$outside || $n!=46554 || $::ot_idx_region_unbound_stage!=0} {error GPL_GROUP_CONSUMPTION_MODEL_FAILED}
puts ACTUAL_GPL_GROUP_CONSUMPTION_PASS
