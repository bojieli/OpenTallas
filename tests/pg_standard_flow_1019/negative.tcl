# Database/API negatives: fresh imported ODB per case, no original changes.
read_db /src/inputs/3_3_place_gp.odb
source /src/physical/common_flow/native_pg_binding.tcl
set block [ord::get_db_block]
global_connect
set master [[ord::get_db] findMaster BUFx8_ASAP7_75t_R]
set first [odb::dbInst_create $block $master pg_first]
set second [odb::dbInst_create $block $master pg_second]
set before [ot_pg_binding_state $block]
set kind $::env(CASE)
switch $kind {
 missing {
  foreach rule [$block getGlobalConnects] {odb::dbGlobalConnect_destroy $rule}
  set expected OT_PG_UNKNOWN_DOMAIN
 }
 protected {$second setDoNotTouch 1;set expected OT_PG_ORDER_PROTECTED_UNBOUND}
 wrong {
  [$second findITerm VDD] connect [$block findNet VSS]
  set before [ot_pg_binding_state $block]
  set expected OT_PG_WRONG_DOMAIN
 }
 ambiguous - signal {
  set net [$block findNet VDD]
  if {$kind eq "ambiguous"} {
   set net [odb::dbNet_create $block OTHER_POWER]
   $net setSigType POWER
   set pin {^VDD$}
   set expected OT_PG_AMBIGUOUS_DOMAIN
  } else {set pin {^A$};set expected OT_PG_RULE_SIGNAL_PIN}
  odb::dbGlobalConnect_create $net NULL {^pg_second$} $pin
 }
 pattern {
  odb::dbGlobalConnect_create [$block findNet VDD] NULL {^pg_second$} {^VD[D]$}
  set expected OT_PG_UNSUPPORTED_PIN_PATTERN
 }
 stage {
  set ::env(SCRIPTS_DIR) /src/tests/pg_standard_flow_1019
  if {![catch {ot_pg_require_cts_source_context} why] || $why ne "OT_PG_PARASITICS_STAGE_REFUSED"} {error STAGE_NOT_REFUSED}
  if {[ot_pg_binding_state $block] ne $before} {error REFUSAL_MUTATED}
  puts STAGE_AUTHORITY_REFUSAL_PASS
  exit
 }
}
if {![catch {ot_pg_bind_batch_before_protect $block [list $first $second]} why] || ![string match "$expected*" $why]} {error "EXPECTED_REFUSAL_MISSING $kind $why"}
if {[ot_pg_binding_state $block] ne $before} {error REFUSAL_MUTATED}
if {$kind eq "protected" && ![$second isDoNotTouch]} {error PROTECTION_CLEARED}
puts "BATCH_PREFLIGHT_REFUSAL_PASS $kind $why"
exit
