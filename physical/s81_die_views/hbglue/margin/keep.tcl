# Margin glue (MARGIN=1, MIN_DEPTH=2): 30,720 retained minimum-delay cells (2 per bit per skew/broadcast stage).
set cells [get_cells -hierarchical *u_min_delay]
if {[llength $cells]!=30720} {error "expected 30720 retained minimum-delay cells, got [llength $cells]"}
set_dont_touch $cells
puts "OT_HEAD_MIN_DELAY_CELLS actual=[llength $cells] dont_touch=1"
