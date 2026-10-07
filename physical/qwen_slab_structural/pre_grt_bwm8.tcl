# PRE_GLOBAL_ROUTE_TCL for --bw-m8: pre_ref.tcl, then M8 is kept for the block-word / tree-word pin nets only.
# The slab's own logic routes M2-M7 as in r11c; M8 capacity is removed (95 %) everywhere except a 60 um strip at the
# left (array-facing) face where the bw_/tw_ M8 pins sit, so the bw/tw nets drop from M8 to M7 inside that strip.
# (s12 without it: M8 opened to every net, DRT-0255 in a ROM-bank worker at x 40 um, 3rd iteration.)
source $::env(QSS_SDC_DIR)/pre_ref.tcl
set qss_die [[ord::get_db_block] getDieArea]
set qss_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set_global_routing_region_adjustment [list 60.0 0.0 [expr {[$qss_die xMax] / double($qss_dbu)}] [expr {[$qss_die yMax] / double($qss_dbu)}]] -layer M8 -adjustment 0.95
puts "QSS M8 reserved for the bw/tw pin strip (x < 60 um)"
