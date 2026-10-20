# Minimum native command composition, NOT a canonical ORFS physical route.
set ::env(OT_PG_STRICT) 0
set ::env(SCRIPTS_DIR) [file dirname [info script]]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach name {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} {read_liberty $plat/lib/NLDM/$name}
read_db /src/inputs/3_3_place_gp.odb
read_sdc /src/inputs/3_place.sdc
source $plat/setRC.tcl
source /src/physical/common_flow/native_pg_binding.tcl
set blk [ord::get_db_block]
# Authorized initial fixture construction, BEFORE the diagnostic insertion run.
# The immutable imported source ODB is never changed on disk.
global_connect
ot_pg_assert_all_native $blk [ot_pg_prepare $blk]
proc repair_timing_helper {} {
  repair_timing -hold -hold_margin 30
  return actual_native_repair
}
if {$::env(CASE) eq "old"} {
  source /src/tests/pg_standard_flow_1019/old_clk_net_protect.tcl
} elseif {$::env(CASE) eq "omit_post"} {
  source /src/tests/pg_standard_flow_1019/omit_post_clk_net_protect.tcl
} else {
  source /src/physical/common_flow/clk_net_protect.tcl
}
# Real native CTS, including real open-output load cells if its balancing adds them.
clock_tree_synthesis -buf_list BUFx8_ASAP7_75t_R -root_buf BUFx8_ASAP7_75t_R -sink_clustering_enable -repair_clock_nets
estimate_parasitics -placement
set before [ot_pg_collect_all_native $blk [ot_pg_prepare $blk]]
puts "FIXTURE_AFTER_CTS unbound=[dict get $before failure_count]"
set rc [catch {repair_timing_helper} result]
if {$rc} {error "NATIVE_REPAIR_FAILED $result"}
if {$result ne "actual_native_repair"} {error RETURN_VALUE_CHANGED}
# Native global_connect is causally too late after old protection: it skips DNT.
if {$::env(CASE) eq "old"} {global_connect}
set after [ot_pg_collect_all_native $blk [ot_pg_prepare $blk]]
set unbound [dict get $after failure_count]
puts "FIXTURE_AFTER_REPAIR unbound=$unbound"
ot_pg_audit_snapshot $blk /src/output/$::env(CASE)/native_pg.json
if {$::env(CASE) eq "old"} {
  if {$unbound == 0} {error OLD_PROTECTION_NEGATIVE_NOT_CAUGHT}
  puts OLD_PROTECTION_CAUSAL_CAUGHT
} elseif {$::env(CASE) eq "omit_post"} {
  if {$unbound != 66} {error "OMITTED_POST_REPAIR_NOT_CAUGHT $unbound"}
  puts OMIT_POST_REPAIR_CAUSAL_CAUGHT
} else {
  if {$unbound != 0} {error NEW_ALL_ROLES_FAILED}
  if {$::ot_pg_bindings_dirty != 0} {error PLACEMENT_RC_DIRTY}
  ot_pg_assert_all_native $blk [ot_pg_prepare $blk]
  puts STANDARD_NATIVE_CTS_REPAIR_BOUNDARY_PASS
}
# Strict guard runs before the real native command; no capability env can waive it.
set ::env(OT_PG_STRICT) 1
ot_pg_install_unsupported_birth_guards
foreach command {buffer_ports repair_clock_inverters clock_tree_synthesis repair_timing repair_design global_placement} {
  if {![catch {$command} why] || ![string match "OT_PG_NATIVE_BIRTH_CAPABILITY_REQUIRED command=$command" $why]} {error "STRICT_NATIVE_GUARD_FAILED $command $why"}
}
puts STRICT_UNSUPPORTED_NATIVE_BIRTH_REFUSAL_PASS
exit
