# Q-TILE45 r6 g3 fences. No timing exceptions.
set q45_max_sinks 15000
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa0 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa1 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa2 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa3 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa4 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_boxes ck_rs {{149.688 513.0 308.232 648.258}}
dict set q45_boxes ck_rn {{22.464 785.04 435.456 818.64}}
dict set q45_boxes ck {{335.016 342.6 435.456 507.6}}
dict set q45_boxes ck_fa0 {}
dict set q45_boxes ck_fa1 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa3 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
