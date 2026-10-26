# FLOW 10-25: the kit's post-GRT repair (FF-only corner here), then vclk back to the SDC (TT) value
source /work/post_grt_drv.tcl
if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }
