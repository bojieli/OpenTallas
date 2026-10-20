source /audit/native_pg_binding.tcl
read_db $::env(OT_PG_AUDIT_ODB)
ot_pg_standard_bind diagnostic_inmemory_only
set fh [open $::env(OT_PG_AUDIT_REPORT) {WRONLY CREAT EXCL}]
set report [ot_pg_write_snapshot [ord::get_db_block] $fh]
puts "DIAGNOSTIC_POST_BIND [dict get $report failure_count]"
exit
