# Native boundary *diagnostic* from CTS placement RC. This is never a routed
# view, never installed in physical/.../views, and cannot qualify a parent.
# Captured /src and /work must be the exact pre_route_gate run.
source /src/tools/ref_tile/path_classes.tcl
file mkdir /work/native_cts_diagnostic
write_timing_model -library_name qfd_xs_leaf_banked_cts_diagnostic_tt /work/native_cts_diagnostic/qfd_xs_leaf_banked_tt.lib
puts "DVM_CTS_NATIVE_DIAGNOSTIC placement_RC_only=1 routed_qualified=0"
