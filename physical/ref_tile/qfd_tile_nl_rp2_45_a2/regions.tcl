# HELD geometry only. No timing exceptions.
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa4 {pin_anchored: every sink is an input pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_rp0 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp1 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp2 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp3 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp4 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp5 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp6 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp7 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp8 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_why ck_rp9 {unfenced: one macro per root, sinks cluster at its pins; relay stages free to spread to consumers}
dict set q45_boxes ck {{331.992 369.36 433.296 505.44}}
dict set q45_boxes ck_rp0 {}
dict set q45_boxes ck_rp5 {}
dict set q45_boxes ck_rp1 {}
dict set q45_boxes ck_rp6 {}
dict set q45_boxes ck_rp2 {}
dict set q45_boxes ck_rp7 {}
dict set q45_boxes ck_rp3 {}
dict set q45_boxes ck_rp8 {}
dict set q45_boxes ck_rp4 {}
dict set q45_boxes ck_rp9 {}
dict set q45_boxes ck_rqr0 {{151.848 515.16 306.072 534.6}}
dict set q45_boxes ck_rqr1 {{164.808 801.414 294.408 816.48}}
dict set q45_boxes ck_tx0 {{77.544 369.36 82.512 505.44}}
dict set q45_boxes ck_tx1 {{77.544 198.72 82.512 334.8}}
dict set q45_boxes ck_tx2 {{77.544 28.08 82.512 164.16}}
dict set q45_boxes ck_tx3 {{317.304 369.36 322.272 505.44}}
dict set q45_boxes ck_tx4 {{317.304 198.72 322.272 334.8}}
dict set q45_boxes ck_tx5 {{317.304 28.08 322.272 164.16}}
dict set q45_boxes ck_tx6 {{437.184 198.72 453.6 334.8}}
dict set q45_boxes ck_tx7 {{437.184 28.08 453.6 164.16}}
dict set q45_boxes ck_fa2 {{2.16 262.16 17.064 362.66}}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
