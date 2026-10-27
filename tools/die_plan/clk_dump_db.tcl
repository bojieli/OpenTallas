# FLOW-CLKFREEZE: standalone clock-net geometry dump of an ODB (openroad -no_init -exit clk_dump_db.tcl)
#   env OT_DB (odb), OT_OUT (tsv), OT_TAG (label), OT_NETS (optional: clk_freeze_nets.txt of the pre-ECO session)
source [file join [file dirname [info script]] clk_freeze.tcl]
read_db $::env(OT_DB)
set nf [expr {[info exists ::env(OT_NETS)] ? $::env(OT_NETS) : ""}]
ot_clk_dump $::env(OT_OUT) [expr {[info exists ::env(OT_TAG)] ? $::env(OT_TAG) : "db"}] $nf
