# S81-TILES-D 10-20: release dont_touch on the landing rings' local cells before GRT repair (RSZ-3006: a kept read_oh
# flop is a dont_touch LOAD of a net repair_design must buffer).  Cells, nets and Yosys keep/merge protection unchanged.
set ot_ldt_n 0
foreach ot_ldt_i [[ord::get_db_block] getInsts] {
  if {[string match "u_lpl_*" [$ot_ldt_i getName]] && [$ot_ldt_i isDoNotTouch]} { $ot_ldt_i setDoNotTouch 0; incr ot_ldt_n }
}
puts "OT_LANDING_DONT_TOUCH_RELEASED $ot_ldt_n"
