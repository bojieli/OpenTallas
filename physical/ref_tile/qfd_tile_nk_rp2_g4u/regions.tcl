# Compact actual sink groups; unchanged timing and placement checks.
set q45_max_sinks 15000
set q45_boxes [dict create]
set q45_why [dict create]
dict set q45_why ck_fa0 {pin_anchored: fixed FIRM boundary registers}
dict set q45_why ck_fa1 {pin_anchored: fixed FIRM boundary registers}
dict set q45_why ck_fa2 {pin_anchored: fixed FIRM boundary registers}
dict set q45_why ck_fa3 {pin_anchored: fixed FIRM boundary registers}
dict set q45_why ck_fa4 {pin_anchored: fixed FIRM boundary registers}
dict set q45_boxes ck {{335.016 342.6 435.456 551.0}}
dict set q45_boxes ck_rn {{164.16 552.96 293.76 585.36}}
dict set q45_boxes ck_rs {{164.16 587.52 293.76 619.92}}
dict set q45_boxes ck_rp3 {{20.304 639.312 146.448 676.032}}
dict set q45_boxes ck_rp8 {{311.472 639.312 437.616 676.032}}
dict set q45_boxes ck_rp4 {{20.304 678.192 146.448 714.936}}
dict set q45_boxes ck_rp9 {{311.472 678.192 437.616 714.936}}
dict set q45_boxes ck_rp0 {{20.304 851.616 146.448 888.336}}
dict set q45_boxes ck_rp2 {{165.888 851.616 292.032 888.336}}
dict set q45_boxes ck_rp5 {{311.472 851.616 437.616 888.336}}
dict set q45_boxes ck_rp1 {{20.304 890.496 146.448 927.24}}
dict set q45_boxes ck_rp7 {{165.888 890.496 292.032 927.24}}
dict set q45_boxes ck_rp6 {{311.472 890.496 437.616 927.24}}
dict set q45_boxes ck_fa0 {}
dict set q45_boxes ck_fa1 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa3 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
