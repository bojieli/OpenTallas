# HELD geometry only. No timing exceptions.
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa4 {pin_anchored: every sink is an input pin flop fixed FIRM at its pin by io_flop_at_pins}
dict set q45_why ck_fa2 {pin_anchored: every sink is an output launch flop fixed FIRM at its pin by io_flop_at_pins (OT_OFLOP)}
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
dict set q45_why ck_tx0 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx1 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx2 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx3 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx4 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx5 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx6 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_why ck_tx7 {unfenced: sinks are one LSL face register bank wired only to that LSL face; 5-11 um fences broke DPO (DPL-0200)}
dict set q45_boxes ck {{365.04 369.36 405.0 505.44}}
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
dict set q45_boxes ck_rqr0 {{151.848 524.88 306.072 534.6}}
dict set q45_boxes ck_rqr1 {{164.808 807.84 294.408 816.48}}
dict set q45_boxes ck_tx0 {}
dict set q45_boxes ck_tx1 {}
dict set q45_boxes ck_tx2 {}
dict set q45_boxes ck_tx3 {}
dict set q45_boxes ck_tx4 {}
dict set q45_boxes ck_tx5 {}
dict set q45_boxes ck_tx6 {}
dict set q45_boxes ck_tx7 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
