source /work/native_pg_binding.tcl
read_db /input/3_place.odb
set b [ord::get_db_block]
set r [ot_pg_audit_snapshot $b /work/pg_before_repair.json]
if {[dict get $r failure_count] != 27094} {error HROOT_PG_REPAIR_UNEXPECTED_INPUT_COUNT}
foreach row [dict get $r failures] {
 if {[dict get $row reason] ne "OT_PG_FINAL_BINDING" || [dict get $row actual_net] ne ""} {error HROOT_PG_REPAIR_UNEXPECTED_CLASS}
 set i [$b findInst [dict get $row instance]]
 if {$i eq "NULL" || ![string match BUF* [[$i getMaster] getName]]} {error HROOT_PG_REPAIR_UNEXPECTED_INSTANCE}
 if {[$i isDoNotTouch]} {error "HROOT_PG_REPAIR_PROTECTED_UNBOUND [$i getName]"}
}
# Existing persisted VDD/VSS rules only. No new rules, clearing protection or signal edits.
global_connect
set r [ot_pg_audit_snapshot $b /work/pg_after_repair.json]
if {[dict get $r failure_count] != 0} {error HROOT_PG_REPAIR_NOT_CLOSED}
write_db /work/hroot_pg_bound.odb
puts HROOT_EXISTING_RULE_PG_COPY_COMPLETE
