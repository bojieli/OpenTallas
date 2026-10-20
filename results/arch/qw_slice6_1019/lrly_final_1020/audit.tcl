read_db /work/$::env(LEAF).odb
source /work/native_pg_binding.tcl
ot_pg_audit_snapshot [ord::get_db_block] /work/$::env(LEAF)_native_pg.json
exit
