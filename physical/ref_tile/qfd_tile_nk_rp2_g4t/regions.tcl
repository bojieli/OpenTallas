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
dict set q45_boxes ck_rn {{212.328 550.8 255.528 572.4}}
dict set q45_boxes ck_rs {{212.328 586.98 255.528 608.58}}
dict set q45_boxes ck_rp3 {{20.304 639.312 146.448 654.432}}
dict set q45_boxes ck_rp8 {{311.472 639.312 437.616 654.432}}
dict set q45_boxes ck_rp4 {{20.304 656.616 146.448 671.736}}
dict set q45_boxes ck_rp9 {{311.472 656.616 437.616 671.736}}
dict set q45_boxes ck_rp0 {{20.304 808.416 146.448 823.536}}
dict set q45_boxes ck_rp2 {{165.888 808.416 292.032 823.536}}
dict set q45_boxes ck_rp5 {{311.472 808.416 437.616 823.536}}
dict set q45_boxes ck_rp1 {{20.304 825.72 146.448 840.84}}
dict set q45_boxes ck_rp7 {{165.888 825.72 292.032 840.84}}
dict set q45_boxes ck_rp6 {{311.472 825.72 437.616 840.84}}
dict set q45_boxes ck_fa0 {}
dict set q45_boxes ck_fa1 {}
dict set q45_boxes ck_fa2 {}
dict set q45_boxes ck_fa3 {}
dict set q45_boxes ck_fa4 {}
source /src/tools/qwen_repack/localize45.tcl
