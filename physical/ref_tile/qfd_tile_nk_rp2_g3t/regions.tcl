# Q-TILE45 r6 g3L fences. No timing exceptions.
set q45_max_sinks 15000
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa0 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa1 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa2 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa3 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa4 {pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_boxes ck_rn {{149.688 513.0 308.232 734.706} {17.064 639.312 149.688 671.736} {308.232 639.312 440.856 671.736}}
dict set q45_boxes ck_rs {{17.064 808.416 440.856 840.84} {22.464 914.55 435.456 948.24}}
dict set q45_boxes ck {{335.016 342.6 435.456 551.0}}
dict set q45_boxes ck_fa0 {}
dict set q45_boxes ck_fa1 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa3 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
