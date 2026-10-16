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
dict set q45_boxes ck {{329.832 367.2 435.456 507.6}}
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
dict set q45_boxes ck_rqr0 {{149.688 513 308.232 536.76}}
dict set q45_boxes ck_rqr1 {{162.648 799.254 296.568 818.64}}
dict set q45_boxes ck_tx0 {{75.384 367.2 84.672 507.6}}
dict set q45_boxes ck_tx1 {{75.384 196.56 84.672 336.96000000000004}}
dict set q45_boxes ck_tx2 {{75.384 25.92 84.672 166.32}}
dict set q45_boxes ck_tx3 {{315.144 367.2 324.432 507.6}}
dict set q45_boxes ck_tx4 {{315.144 196.56 324.432 336.96000000000004}}
dict set q45_boxes ck_tx5 {{315.144 25.92 324.432 166.32}}
dict set q45_boxes ck_tx6 {{435.024 196.56 455.76 336.96000000000004}}
dict set q45_boxes ck_tx7 {{435.024 25.92 455.76 166.32}}
dict set q45_boxes ck_fa2 {{2.16 262.16 17.064 362.66}}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
