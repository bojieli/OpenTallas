# Physical minimum-delay cells are architectural, not optional repair buffers.
set cells [get_cells -hierarchical *u_min_delay]
if {[llength $cells]!=15424} {error "expected15424 retained minimum-delay cells, got[llength $cells]"}
set_dont_touch $cells
puts "OT_HEAD_MIN_DELAY_CELLS actual=[llength $cells] dont_touch=1"
