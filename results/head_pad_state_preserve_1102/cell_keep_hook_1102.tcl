# DH54-PAD successor of 69812606f generic_cell_keep_hook.tcl (that file is unchanged).
# The packet hook's exact selector head_pad_fragment/w:g_baseline.state FAILS CLOSED on the pinned yosys 0.68+post
# Verilog frontend: the nested if/else generate names the wire \genblk1.genblk1.g_baseline.state (measured, m0_cellkeep
# canonicalize log 11-02). Only the selector differs; the recipe is the same: wire keep on the exact projected state,
# then the real repository hook (proc, per-bit techmap of the kept FF, per-bit cell KEEP).
if {![info exists ::env(OT_HEAD_PAD_KEEP_PROFILE)] || $::env(OT_HEAD_PAD_KEEP_PROFILE) eq "0"} { return }
if {$::env(OT_HEAD_PAD_KEEP_PROFILE) ne "1"} { error "invalid pad keep profile" }
yosys select -assert-count 1 {head_pad_fragment/w:genblk1.genblk1.g_baseline.state}
yosys setattr -set keep 1 {head_pad_fragment/w:genblk1.genblk1.g_baseline.state}
source /work/ot_keep_regs.reference.tcl
