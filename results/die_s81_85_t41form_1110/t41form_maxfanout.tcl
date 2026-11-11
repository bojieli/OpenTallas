# T41FORM (DIE-S81-85 t41form 11-10) PRE_RESIZE hook: re-assert set_max_fanout 24 on the stage SDC before 3_4 repair_design.
set_max_fanout 24 [current_design]
puts "T41FORM set_max_fanout 24 (pre-resize)"
