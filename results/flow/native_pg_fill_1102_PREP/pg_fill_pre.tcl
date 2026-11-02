# HELD adapter: source-only. Original hook file must preserve the actual PRE.
source /work/native_pg_binding_fill_candidate.tcl
if {![ot_pg_strict_enabled]} {error OT_PG_FILL_STRICT_ONE_REQUIRED}
ot_pg_native_birth_begin /work/nativepgbirth.so
source /work/pg_fill_original_pre.tcl
