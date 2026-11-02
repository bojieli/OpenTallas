# PREP ONLY: install via existing SYNTH_CANONICALIZE_TCL in a fresh fragment kit.
# Fail closed if exact wire selection changed with the chosen frontend.
if {![info exists ::env(OT_HEAD_PAD_KEEP_PROFILE)] || $::env(OT_HEAD_PAD_KEEP_PROFILE) eq "0"} { return }
if {$::env(OT_HEAD_PAD_KEEP_PROFILE) ne "1"} { error "invalid pad keep profile" }
yosys select -assert-count 1 {head_pad_fragment/w:g_baseline.state}
yosys setattr -set keep 1 {head_pad_fragment/w:g_baseline.state}
# Real repository hook: proc, selected per-bit techmap, per-bit FF KEEP.
# OT_PIN_REGS/OT_RST_LAND/OT_KEEP_PIN_REGS/OT_KEEP_WIRES/OT_RST_COPIES_MAX/
# OT_LANDING_FF must all be absent/0 in this isolated coupon.
source /work/ot_keep_regs.reference.tcl
