# Independent saved-DB read. No native module load, callback, repair or STA.
set ::env(OT_PG_STRICT) 1
source /work/pg_native_qualified_562.tcl
source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_place.odb 3_place.sdc
if {[info commands ot_native_pg_install] ne ""} {error READ_ONLY_AUDIT_MUST_NOT_HAVE_NATIVE_MODULE}
set block [ord::get_db_block]
ot_pg_audit_snapshot $block /case/SAVED_PLACE_PG_AUDIT.json
set checked [ot_pg_assert_all_native $block [ot_pg_prepare $block]]
puts "INDEPENDENT_SAVED_PLACE_PG_PASS checked=$checked repair=0 STA=0"
