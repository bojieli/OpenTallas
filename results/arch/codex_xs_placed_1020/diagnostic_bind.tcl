# Diagnostic only: changes in-memory clone, never writes an ODB or relaxes protection.
source /audit/native_pg_binding.tcl
read_db $::env(AUDIT_ODB)
global_connect
ot_pg_audit_snapshot [ord::get_db_block] $::env(AUDIT_OUT)
exit
