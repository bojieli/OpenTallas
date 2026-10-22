source /src/physical/common_flow/native_pg_binding.tcl
read_db /base/4_1_cts.odb
ot_pg_audit_snapshot [ord::get_db_block] /out/pg_4_1_cts.json
exit
