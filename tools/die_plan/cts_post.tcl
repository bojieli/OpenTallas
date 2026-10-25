# GENERATED-COPY of tools/die_plan/cts_post.tcl (POST_CTS hook, FLOW 2026-10-25): tap trees balanced to the bound
# insertion (tap_balance.tcl), then register pairs with no logic between them moved onto one clock leaf
# (leaf_affinity.tcl, F4; OT_LEAF_AFFINITY=0 turns it off).
# ORFS sources POST_CTS inside a procedure. Both helpers define global procs
# whose state must live at global scope too.
set cp_dir [file dirname [file normalize [info script]]]
uplevel #0 [list source [file join $cp_dir tap_balance.tcl]]
if {![info exists ::env(OT_LEAF_AFFINITY)] || $::env(OT_LEAF_AFFINITY) ne "0"} { uplevel #0 [list source [file join $cp_dir leaf_affinity.tcl]] }
