# Step hook (hgi-1010/idleB 2026-10-10): keep the retained minimum-delay cells of ot_s81_head_min_buffer (u_min_delay,
# BUFx2_ASAP7_75t_R; HOLDBUF / HOLDLINE hold floors) through every resizer step: dont_touch, so repair_design /
# repair_timing / remove_buffers neither delete nor resize them.  OT_MIN_DELAY_EXPECT (optional) = the exact count.
set ot_md_cells [get_cells -hierarchical *u_min_delay]
set ot_md_n [llength $ot_md_cells]
if {[info exists ::env(OT_MIN_DELAY_EXPECT)] && $ot_md_n != $::env(OT_MIN_DELAY_EXPECT)} {
  error "OT_MIN_DELAY_KEEP expected $::env(OT_MIN_DELAY_EXPECT) retained minimum-delay cells, got $ot_md_n"
}
if {$ot_md_n == 0} { error "OT_MIN_DELAY_KEEP: no retained minimum-delay cells (u_min_delay) in the design" }
set_dont_touch $ot_md_cells
puts "OT_MIN_DELAY_KEEP cells=$ot_md_n dont_touch=1"
