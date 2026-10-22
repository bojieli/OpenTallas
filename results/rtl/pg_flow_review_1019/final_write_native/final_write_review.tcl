source /proof/native_pg_binding.tcl
read_db /clone/source_order_clone.odb
set ::env(OT_PG_STRICT) 1
set b [ord::get_db_block]
ot_pg_install_final_write_guard
file mkdir /proof/clean_final
write_db /proof/clean_final/6_final.odb
puts FINAL_PREBOUND_ACTUAL_WRITE_PASS
set master NULL
foreach inst [$b getInsts] {
 if {[[ $inst getMaster] getName] eq "BUFx24_ASAP7_75t_R"} {set master [$inst getMaster];break}
}
if {$master eq "NULL"} {error NO_NATIVE_BUFFER_MASTER}
set late [odb::dbInst_create $b $master ot_pg_review_late_unprotected]
file mkdir /proof/late_final
if {![catch {write_db /proof/late_final/6_final.odb} reason] || ![string match *OT_PG_FINAL_LATE_BINDING_REFUSED* $reason]} {error "LATE_NEGATIVE_MISSING $reason"}
foreach pin {VDD VSS} {if {[[$late findITerm $pin] getNet] ne "NULL"} {error FINAL_GUARD_REPAIRED_LATE_TERM}}
if {[file exists /proof/late_final/6_final.odb]} {error FINAL_FAILURE_WROTE_ODB}
puts "EXPECTED_LATE_UNPROTECTED_REFUSAL $reason unchanged_unbound2"
ot_pg_install_rc_observers
# The native global rule API can bind actual terms even when the explicit
# pre-protection binder is never called. Whole-state observers must see it.
add_global_connection -net VDD -inst_pattern ^ot_pg_review_late_unprotected$ -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern ^ot_pg_review_late_unprotected$ -pin_pattern {^VSS$} -ground
if {![info exists ::ot_pg_bindings_dirty] || $::ot_pg_bindings_dirty != 2} {error "HIDDEN_GLOBAL_DELTA_NOT_SEEN $::ot_pg_bindings_dirty"}
if {![catch {write_db /proof/late_final/6_final.odb} reason] || ![string match *OT_PG_FINAL_RC_DIRTY_REFUSED* $reason]} {error "DIRTY_NEGATIVE_MISSING $reason"}
puts "EXPECTED_HIDDEN_RULE_BINDING_REFUSAL $reason actual_delta=2 explicit_binder_calls=0"
puts FINAL_WRITE_MODEL_REVIEW_PASS
exit
