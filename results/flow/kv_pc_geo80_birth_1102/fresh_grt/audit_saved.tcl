# Independent reopened saved-DB audit; no module, callback, PG connect, repair or STA.
set ::env(OT_PG_STRICT) 1
source /work/native_pg_binding.tcl
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
if {[info commands ot_native_pg_install] ne ""} {error READ_ONLY_AUDIT_MUST_NOT_HAVE_NATIVE_MODULE}
set b [ord::get_db_block]
ot_pg_audit_snapshot $b /work/SAVED_GRT_PG_AUDIT.json
set checked [ot_pg_assert_all_native $b [ot_pg_prepare $b]]
puts "INDEPENDENT_SAVED_GRT_PG_PASS checked=$checked repair=0 STA=0"
