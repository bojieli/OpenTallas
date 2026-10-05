# Standalone pre-route gate (2026-10-03, results/uarch/macro_pin_access_audit_20261003): attach to any
# run, whatever its macro placement hook, with
#     --step-tcl POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl
# (tools/run_abi3_physical_aligned.py --macro-track-gate adds it).  POST_TAPCELL runs after macro
# placement and before PDN, global placement and routing: an off-track macro pin fails the run in
# minutes instead of DRT-0255 hours later.  Pinned hooks stay byte-identical.
source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] physical/common/ot_macro_track_snap.tcl]
ot_mts::assert_on_track -label POST_TAPCELL
