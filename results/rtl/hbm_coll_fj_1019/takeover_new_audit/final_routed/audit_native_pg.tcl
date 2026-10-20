# Read-only native audit. Report is exclusively created, including failures.
source [file join [file dirname [info script]] native_pg_binding.tcl]
if {![info exists ::env(OT_PG_AUDIT_ODB)] || ![info exists ::env(OT_PG_AUDIT_REPORT)]} {error OT_PG_AUDIT_ENV}
if {[file exists $::env(OT_PG_AUDIT_REPORT)]} {puts stderr OT_PG_AUDIT_REPORT_EXISTS; exit 3}
set fh [open $::env(OT_PG_AUDIT_REPORT) {WRONLY CREAT EXCL}]
if {[catch {read_db $::env(OT_PG_AUDIT_ODB)} why]} {
  puts $fh "\{\"schema\":\"native_pg_audit.v1\",\"status\":\"REFUSED\",\"reason\":[ot_pg_json_string $why]\}"
  close $fh
  puts stderr $why
  exit 2
}
if {[catch {ot_pg_write_snapshot [ord::get_db_block] $fh} report]} {puts stderr $report; exit 2}
if {[dict get $report failure_count] > 0} {puts stderr "OT_PG_AUDIT_FAIL [dict get $report failure_count]"; exit 2}
puts "OT_PG_AUDIT_PASS [dict get $report checked]"
exit
