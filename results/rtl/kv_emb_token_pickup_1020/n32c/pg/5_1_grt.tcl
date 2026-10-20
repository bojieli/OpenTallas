source /src/physical/common_flow/native_pg_binding.tcl
read_db /base/5_1_grt.odb
ot_pg_audit_snapshot [ord::get_db_block] /out/pg_5_1_grt.json
exit
