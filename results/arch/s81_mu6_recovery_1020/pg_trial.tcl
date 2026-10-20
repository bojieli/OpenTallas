read_db $::env(AUDIT_ODB)
set block [ord::get_db_block]
puts "ORIGINAL_NATIVE_GLOBAL_RULES [llength [$block getGlobalConnects]]"
global_connect
write_db /audit/trial_global_connect.odb
exit
