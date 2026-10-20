read_db $::env(TEST_ODB)
# Explicitly constructed all-bound zero-SPEF TEST fixture, before any analysis.
global_connect
source /src/physical/common_flow/native_pg_binding.tcl
ot_pg_assert_all_native [ord::get_db_block] [ot_pg_prepare [ord::get_db_block]]
write_db $::env(TEST_FIXTURE)
puts TEST_ALLBOUND_FIXTURE_CREATED
