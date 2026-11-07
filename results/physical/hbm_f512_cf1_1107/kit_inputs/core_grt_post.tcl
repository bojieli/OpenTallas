if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }
uplevel #0 [list source /work/pg_connect.tcl]
ot_pg_connect_all grt_post
ot_pg_require_bound grt_post
