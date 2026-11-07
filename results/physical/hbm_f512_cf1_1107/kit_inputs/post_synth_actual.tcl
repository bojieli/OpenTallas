source /work/face_keep_release.tcl
# Preserve the actual post-eliminate_dead_logic graph for face_guard.
write_verilog $::env(RESULTS_DIR)/1_synth.v
