# QC-SU-F4B (COORD RULING QC-SU-F4A-SIGN): plan layer assignment of the clock TREE nets (ot_ms_*_n: root/trunk/island
# feeds/branch nets, every net between two plan tree cells) to M5 (vertical) + M6 (horizontal) only; leaf nets
# (ot_ms_*_clk, flop/SRAM clock pins) stay on the signal stack M2-M5.  Why: F4A RCX (points 6/7) showed the late islands
# are the feeds that DRT routed on M4 through the pin-register bands: PG via-stack ladders + track-hopping zig-zags with
# 8-15 fF coupling (incl. self-coupling) where clean feeds have < 1 fF.  M6 is empty inside the core (signals <= M5, PDN =
# M1/M2 rails + M5 straps), so a horizontal M6 leg has no PG vias and no neighbours; vertical M5 legs run between straps.
# Each 2-pin leg = one L (<= 1 V5 at the bend) + the pin via stacks at its two ends.  No cell, size, position or clock
# timing change; no pads/trims (12.8).  The core abstract carries the M6 shapes as OBS (die-plan item).
set blk [ord::get_db_block]
set ntree 0; set nleaf 0
foreach n [$blk getNets] {
  set nm [$n getName]
  if {![string match ot_ms_* $nm]} continue
  if {[string match *_n $nm]} { $n setSigType CLOCK; incr ntree } else { $n setSigType SIGNAL; incr nleaf }
}
set_routing_layers -signal M2-M5 -clock M5-M6
puts "F4B_LAYERS tree_nets $ntree -> clock M5-M6 ; leaf/other ot_ms nets $nleaf -> signal M2-M5"
