# The exact source_step_tcl consumer is PRE_FILLCELL_TCL, not PRE_FILLCELL.
source /work/native_pg_binding_fill_candidate.tcl
if {![ot_pg_strict_enabled]} {error OT_PG_FILL_STRICT_ONE_REQUIRED}
ot_pg_native_birth_begin /work/nativepgbirth.so
source /work/pg_fill_original_pre.tcl
# The actual caller marks this only after its input PG0 and full old-state guards.
if {![info exists ::ot_pg_fill_baseline_ready] || $::ot_pg_fill_baseline_ready ne "1"} {error OT_PG_FILL_CALLER_BASELINE_NOT_INITIALIZED}
set ::ot_pg_fill_pre_complete 1
