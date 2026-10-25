# PATH-QC-NL 10-25 A0 NL v10c placement hook (pin_hook_before_flops): regions + NL whitespace blockages + group cones.
# Blockages / cone depth = Codex combined0719 (nl_combined0719_hook.tcl); regions see qfd_tile_nl_a0v10c_regions.tcl.
source /src/tools/qwen_romleaf/repack/qfd_tile_nl_a0v10c_regions.tcl
source /src/tools/qwen_romleaf/a0core/nl_a0v10c_block.tcl
set ::env(OT_A0C_CONES) {hd0 hd1 hd2 hd3 hd4 hd5 hd6 hd7 l2c f0 o0 f1 o1 f2 o2 f3 o3 q3 f4 o4 f5 o5 q5 f6 o6 f7 o7 q7 fltq ctl_is ctl_xm}
set ::env(OT_A0C_CONE_DEPTH) 6
source /src/tools/qwen_romleaf/a0core/a0v8c_extra.tcl
