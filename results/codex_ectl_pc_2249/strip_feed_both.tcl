# Fixed macro-shadow strips; geometry only, same buffer depth, no timing inputs or pads.
proc q2_strip_apply {tag rect west east wtop etop} {
 global env sf_prefix
 set env(OT_SF_PREFIX) $tag
 set env(OT_SF_MODE) chain
 set env(OT_SF_RECT) $rect
 set env(OT_SF_W_XY) $west
 set env(OT_SF_E_XY) $east
 set env(OT_SF_WTOP_XY) $wtop
 set env(OT_SF_ETOP_XY) $etop
 source /work/strip_feed_kernel.tcl
}
q2_strip_apply L {15.12 4.32 109.944 13.26} {11.34 9.45} {113.4 9.45} {11.34 57.24} {113.4 57.24}
q2_strip_apply R {133.488 4.32 228.312 13.26} {129.168 9.45} {230.472 9.45} {129.168 57.24} {230.472 57.24}
