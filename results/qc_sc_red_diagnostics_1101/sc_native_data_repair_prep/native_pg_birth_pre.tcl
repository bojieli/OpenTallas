source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error SC_PG_REQUIRES_STRICT}
ot_pg_native_birth_begin /work/nativepgbirth.so
source /work/sc_grt_pre_reviewed.tcl
