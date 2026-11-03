# Reviewed private native-PG CTS canary; normal mode only, no strict bypass.
source /work/native_pg_binding.tcl
if {[ot_pg_strict_enabled]} {error OT_PG_CTS_NOT_YET_STRICT_ADMITTED}
ot_pg_native_birth_begin /work/nativepgbirth.so
source /work/hold_budget.tcl
