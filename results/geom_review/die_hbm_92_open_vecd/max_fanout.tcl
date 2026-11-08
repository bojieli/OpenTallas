# HBM DRV basis (gen_core_kit_hbm.py --max-fanout): fanout cap at every repair_design
set_max_fanout 8 [current_design]
puts "HBMCORES max_fanout 8"
# vXLK: repeater pitch on every repair_design_helper (place resize + GRT), measured slew class (vK0 FF 120 / TT 282)
if {[info exists ::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) ne ""} { source /work/grt_maxwire.tcl }
