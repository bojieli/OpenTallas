# NK k2rs placement-only recipe; no RTL/data-cycle change.
set ::env(OT_A0C_BLOCK) {}
set ::env(OT_A0C_CONES) {hd0 hd1 hd2 hd3 hd4 hd5 hd6 hd7 l2c f0 o0 f1 o1 f2 o2 f3 o3 f4 o4 f5 o5 q5 f6 o6 f7 o7 q7 fltq}
set ::env(OT_A0C_CONE_DEPTH) 6
source /src/tools/qwen_romleaf/a0core/a0v8c_extra.tcl
