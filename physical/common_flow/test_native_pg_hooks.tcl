# Native fleet test: requires reviewed PG-complete ODB and fresh outputdirectory.
set test_dir [file dirname [info script]]
source $test_dir/native_pg_binding.tcl
read_db $::env(OT_PG_TEST_ODB)
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
# This database-only witness has no timing libraries/RC; actual ORFS CTS replay
# separately verifies the native placement estimator. Count its required dispatch.
rename estimate_parasitics ot_pg_test_native_estimate
set ::ot_pg_test_estimate_count 0
proc estimate_parasitics {args} {incr ::ot_pg_test_estimate_count}
if {![info exists ::env(OT_PG_TEST_PHASE)] || $::env(OT_PG_TEST_PHASE) ne "finish"} {
set inst [odb::dbInst_create $block $master clkbuf_pg_hook_proof]
set clocknet [odb::dbNet_create $block hook_clock]
$clocknet setSigType CLOCK
[$inst findITerm Y] connect $clocknet
set ::env(OT_PG_STRICT) 0
source $test_dir/clk_net_protect.tcl
ot_protect_clock_tree
if {![$inst isDoNotTouch] || [[$inst findITerm VDD] getNet] ne "NULL"} {error DEFAULT_BEHAVIOR_CHANGED}
if {![catch {ot_pg_assert_all_native $block [ot_pg_prepare $block]} msg] || ![string match {*count=2*} $msg]} {error DEFAULT_NEGATIVE_MISSING}
puts DEFAULT_PROTECTED_NEGATIVE_PASS
# Fixture reset only, production hook never clears protection.
$inst setDoNotTouch 0
$clocknet setDoNotTouch 0
odb::dbInst_destroy $inst
odb::dbNet_destroy $clocknet
set inst [odb::dbInst_create $block $master clkbuf_pg_hook_proof]
set clocknet [odb::dbNet_create $block hook_clock]
$clocknet setSigType CLOCK
[$inst findITerm Y] connect $clocknet
set ::env(OT_PG_STRICT) 1
source $test_dir/clk_net_protect.tcl
# A CTS-named replay of the actual routed fixture must refuse even after a
# placement API call. No stage name can authorize a routed-model downgrade.
set ::env(SCRIPTS_DIR) $::env(OT_PG_TEST_OUT)
set fh [open $::env(OT_PG_TEST_OUT)/cts.tcl {WRONLY CREAT EXCL}]
puts $fh {ot_protect_clock_tree}
close $fh
estimate_parasitics -placement
if {![catch {source $::env(OT_PG_TEST_OUT)/cts.tcl} why] || ![string match {*OT_PG_PARASITICS_ROUTED_DB_REFUSED*} $why]} {error ROUTED_CTS_REPLAY_NOT_REFUSED}
if {[$inst isDoNotTouch] || [[$inst findITerm VDD] getNet] ne "NULL"} {error REFUSED_CONTEXT_MUTATED}
# Fixture-only removal of signal wires constructs an unrouted database. It
# qualifies no geometry; released ODB and reviewed clone remain untouched.
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND} || [$net getWire] eq "NULL"} continue
 set protected [$net isDoNotTouch]
 $net setDoNotTouch 0
 odb::dbWire_destroy [$net getWire]
 $net setDoNotTouch $protected
}
write_db $::env(OT_PG_TEST_OUT)/unrouted_fixture.odb
# A mismatching/missing SPEF read invalidates provenance even after a later
# placement estimate; only a successful fresh unrouted read_db clears it.
catch {read_spef $::env(OT_PG_TEST_OUT)/absent.spef}
estimate_parasitics -placement
if {![catch {source $::env(OT_PG_TEST_OUT)/cts.tcl} why] || $why ne "OT_PG_PARASITICS_SPEF_PROVENANCE_REFUSED"} {error SPEF_REPLAY_NOT_REFUSED}
puts ROUTED_CTS_AND_SPEF_REPLAY_REFUSALS_PASS
exit
}
# OpenROAD refuses loading a second database in one native process. The finish
# phase starts a new process on the independently serialized unrouted fixture.
set inst [$block findInst clkbuf_pg_hook_proof]
set ::env(OT_PG_STRICT) 1
source $test_dir/clk_net_protect.tcl
set ::env(SCRIPTS_DIR) $::env(OT_PG_TEST_OUT)
if {![catch {ot_protect_clock_tree} why] || ![string match {*OT_PG_PARASITICS_MODEL_REFUSED*} $why]} {error UNKNOWN_MODEL_NOT_REFUSED}
estimate_parasitics -global_routing
if {![catch {ot_protect_clock_tree} why] || ![string match {*OT_PG_PARASITICS_MODEL_REFUSED*} $why]} {error ROUTED_MODEL_NOT_REFUSED}
estimate_parasitics -placement
if {![catch {ot_protect_clock_tree} why] || $why ne "OT_PG_PARASITICS_STAGE_REFUSED"} {error STAGE_REFUSAL_MISSING}
set ::ot_pg_test_estimate_count 0
estimate_parasitics -placement
source $::env(OT_PG_TEST_OUT)/cts.tcl
if {![$inst isDoNotTouch] || [[$inst findITerm VDD] getNet] eq "NULL"} {error STRICT_HOOK_FAILED}
if {$::ot_pg_test_estimate_count != 2} {error PARASITICS_REFRESH_DISPATCH}
ot_pg_final_guard
set report [ot_pg_audit_snapshot $block $::env(OT_PG_TEST_OUT)/snapshot.json]
if {[dict get $report failure_count]} {error SNAPSHOT_FAILED}
write_db $::env(OT_PG_TEST_OUT)/6_final.odb
set late [odb::dbInst_create $block $master late_unbound]
$late setDoNotTouch 1
if {![catch {write_db $::env(OT_PG_TEST_OUT)/late/6_final.odb} msg] || ![string match {*OT_PG_FINAL_FAIL count=2*} $msg]} {error FINAL_WRITE_NEGATIVE_MISSING}
puts STRICT_HOOK_AND_FINAL_WRITE_PASS
exit
