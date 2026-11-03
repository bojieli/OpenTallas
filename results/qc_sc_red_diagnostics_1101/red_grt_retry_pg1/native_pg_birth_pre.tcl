source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error OT_PG_GRT_REQUIRES_STRICT_MODE}
ot_pg_native_birth_begin /work/nativepgbirth.so
source {/work/grt_pre_reviewed.tcl}
