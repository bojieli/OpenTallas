# Q-TILE45 r6 g3L fences. No timing exceptions.
set q45_max_sinks 15000
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa0 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa1 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa2 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa3 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa4 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_boxes ck_rn {{192.888 513.0 351.432 691.506} {60.264 596.112 192.888 628.536} {351.432 596.112 484.056 628.536}}
dict set q45_boxes ck_rs {{60.264 765.216 484.056 797.64} {65.664 871.35 478.656 905.04}}
dict set q45_boxes ck {{378.216 342.6 478.656 507.6}}
dict set q45_boxes ck_fa0 {}
dict set q45_boxes ck_fa1 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa3 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
