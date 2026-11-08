source /work/face_keep_release.tcl
# Preserve the actual post-eliminate_dead_logic graph for face_guard.
# DIE-HBM-92-OPEN/VECD vXLK: cross-root lockup latches (vecd_xlk.tcl), then the netlist the rest of the flow uses.
source /work/vecd_xlk.tcl
write_verilog $::env(RESULTS_DIR)/1_synth.v
