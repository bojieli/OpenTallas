# Explicit opt-in; native macro bands only. No invented capacity or PG credit.
if {$::env(ROUTING_LAYER_ADJUSTMENT) != 0.25} {error "Original25percent layer reservation required"}
set n 0
foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] isBlock]} {incr n}}
if {$n != 8} {error "Wrong retained full tile macro inventory"}
set_macro_extension 1
puts "OT_NATIVE_MACRO_BAND cells=1 gcell_um=0.57 macros=8 lower_OBS_layers=M2,M3,M4 PG_unchanged=1 M5_M6_escape=1"
