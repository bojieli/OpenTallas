# DRIVE-S81-CAP 10-20: release INSTANCE dont_touch on non-clock standard cells before the GRT-stage repair_design.
# RSZ-3006 killed every capc5b..h trial GRT: repair_design must buffer a net whose LOAD is dont_touch (5b..f: a kept
# landing read_oh flop u_lpl_11_r/.../_018_; 5g/5h: max_wire_repeat's kept strong INVx13 _2216_ after u_fw.q[66]).
# Kept: clock-tree cells (output net CLOCK), out-pin drivers (ot_outdrv*), hold cells (ot_hs*), hard children.
# Cells, nets, Yosys keep/merge protection and constraints are unchanged.
set ot_gdr_n 0
foreach ot_gdr_i [[ord::get_db_block] getInsts] {
  if {![$ot_gdr_i isDoNotTouch] || [[$ot_gdr_i getMaster] isBlock]} continue
  set ot_gdr_nm [$ot_gdr_i getName]
  if {[string match "ot_outdrv*" $ot_gdr_nm] || [string match "ot_hs*" $ot_gdr_nm]} continue
  set ot_gdr_clk 0
  foreach ot_gdr_it [$ot_gdr_i getITerms] {
    if {[$ot_gdr_it isOutputSignal] && [$ot_gdr_it getNet] ne "NULL" && [[$ot_gdr_it getNet] getSigType] eq "CLOCK"} { set ot_gdr_clk 1 }
  }
  if {$ot_gdr_clk} continue
  $ot_gdr_i setDoNotTouch 0; incr ot_gdr_n
}
puts "OT_GRT_DONT_TOUCH_RELEASED $ot_gdr_n non-clock std cells"
