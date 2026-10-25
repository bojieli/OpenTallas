# NL combined0719: keep vout in the W pocket and move issue/s1/s2 control toward the split_fault landing.
source /src/tools/qwen_romleaf/repack/qfd_tile_nl_a0v8c_combined0719_regions.tcl
set ::env(OT_A0C_BLOCK) {2.16 658.4 76 885;2.16 1015 76 1155.6;40 885 76 1015;76 1137 455.76 1155.6;435.6 900 455.76 1137}
set ::env(OT_A0C_CONES) {hd0 hd1 hd2 hd3 hd4 hd5 hd6 hd7 l2c ctl_is ctl_xm}
set ::env(OT_A0C_CONE_DEPTH) 6
source /src/tools/qwen_romleaf/a0core/a0v8c_extra.tcl
