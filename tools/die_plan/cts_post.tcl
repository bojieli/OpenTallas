# GENERATED-COPY of tools/die_plan/cts_post.tcl (POST_CTS hook, FLOW 2026-10-25): tap trees balanced to the bound
# insertion (tap_balance.tcl), then register pairs with no logic between them moved onto one clock leaf
# (leaf_affinity.tcl, F4; OT_LEAF_AFFINITY=0 turns it off).
# ORFS sources POST_CTS inside a procedure. Both helpers define global procs
# whose state must live at global scope too.
set cp_dir [file dirname [file normalize [info script]]]
uplevel #0 [list source [file join $cp_dir tap_balance.tcl]]
if {![info exists ::env(OT_LEAF_AFFINITY)] || $::env(OT_LEAF_AFFINITY) ne "0"} { uplevel #0 [list source [file join $cp_dir leaf_affinity.tcl]] }
# FLOW 2026-10-26 PG: every clock/pad/leaf cell created up to here gets its supplies before 4_1_cts.odb is written
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers), then a hard check (OT_PG_OPEN fails CTS).
uplevel #0 [list source [file join $cp_dir pg_connect.tcl]]
ot_pg_connect_all cts_post
ot_pg_require_bound cts_post
