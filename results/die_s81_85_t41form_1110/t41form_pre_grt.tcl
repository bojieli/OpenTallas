# T41FORM (DIE-S81-85 t41form 11-10) PRE_GLOBAL_ROUTE wrapper: set_max_fanout 24, then the kit's own hold_repair_pre.tcl.
set_max_fanout 24 [current_design]
puts "T41FORM set_max_fanout 24 (pre-GRT)"
source /work/hold_repair_pre.tcl
