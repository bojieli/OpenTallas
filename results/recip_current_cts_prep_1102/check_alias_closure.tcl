# Source/ODB-only integration check. No native PG module or CTS constructor.
if {[info exists ::env(OT_PG_STRICT)]} {error SOURCE_CHECK_ORIGINAL_UNSET_CHANGED}
if {[info commands ::clock_tree_synthesis] eq ""} {error SOURCE_CHECK_REAL_CTS_API_MISSING}
if {[info commands ::ot_mcc_cts_orig] ne ""} {error SOURCE_CHECK_ALIAS_NOT_FRESH}
set original_is_proc [expr {[info procs ::clock_tree_synthesis] ne ""}]
if {$original_is_proc} {
 set original_body [info body ::clock_tree_synthesis]
 set original_args [info args ::clock_tree_synthesis]
}
source /src/tools/orfs_hold_mm.tcl
if {$ot_mcc_file ne "/src/physical/common_flow/macro_cts_cluster.tcl"} {error "SOURCE_CHECK_WRONG_INCLUDE $ot_mcc_file"}
if {[info commands ::ot_mcc_cts_orig] eq ""} {error SOURCE_CHECK_REAL_ALIAS_MISSING}
if {$original_is_proc} {
 if {[info body ::ot_mcc_cts_orig] ne $original_body || [info args ::ot_mcc_cts_orig] ne $original_args} {error SOURCE_CHECK_ORIGINAL_API_CHANGED}
 set f [open /case/ORIGINAL_CTS_API_BODY.tcl w]; puts $f $original_body; close $f
} elseif {[info procs ::ot_mcc_cts_orig] ne "" || [interp alias {} ::ot_mcc_cts_orig] ne ""} {error SOURCE_CHECK_FAKE_ORIGINAL_API}
if {![string match *ot_mcc_cts_orig* [info body ::clock_tree_synthesis]]} {error SOURCE_CHECK_WRAPPER_NOT_NORMAL}
read_db /work/run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base/3_place.odb
set macro_count [ot_mcc_count]
if {$macro_count != 0} {error "SOURCE_CHECK_MACRO_CONTEXT_CHANGED $macro_count"}
set requested {-sink_clustering_enable -repair_clock_nets}
set actual [ot_mcc_args $requested]
if {$actual ne $requested} {error "SOURCE_CHECK_FLAGS_CHANGED $actual"}
if {[info commands ot_native_pg_install] ne ""} {error SOURCE_CHECK_MUST_NOT_LOAD_CALLBACK}
puts [list SOURCE_ALIAS_CLOSURE_PASS canonical_include $ot_mcc_file original_public_API_preserved 1 zero_macros $macro_count requested $requested transformed $actual native_CTS_calls 0]
