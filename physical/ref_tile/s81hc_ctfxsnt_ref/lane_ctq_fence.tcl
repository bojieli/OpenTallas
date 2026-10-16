# s4 lane-root compaction (S-ELEM-PQ 2026-10-15 22:40, measured cause of the s3 native capture FAIL 264.15 ps / 436 pins):
# the clk_l (NORM lane) root of the CLOSED s3 route (d8e5e1a77) reached 616 sinks spread over x 0..300 um because the
# ctq replica (u_x.u_q delay lines u_si/u_xi/u_vs/u_vm, 205 sinks, + fcl/fvl captures) was placed by wirelength next to
# the data rows (x 175..300) while the lane pin flops sit at x 8..118.  Result: leaf buffers of 82..120 ps, lane
# insertion 113.9..191.1 ps (spread 77), so every lane input carried 3..6 hold buffers (hold reference = boundary min
# 113.9 vs local 140..190) plus the R - local deviation -> capture 183..264 ps.  Fix (geometry only, same RTL, same
# registers and cycles): fence every named ctq-replica register into a band directly beside the lane pins
# (x 121..166, full core height, between cs_* (<= 118.04) and the fd_in/fdx pins (>= 169.98)); the clk_l tree then
# spans x 8..166 instead of 0..300.  ABC leaves combinational cells anonymous: they follow by wirelength.
set ::lcf_blk [ord::get_db_block]
set ::lcf_dbu [$::lcf_blk getDbUnitsPerMicron]
set ::lcf_core [$::lcf_blk getCoreArea]
set ::lcf_x0 121.0; set ::lcf_x1 166.0
# s4b: the region edges sit on the 0.054-um site grid of the core (s4 gate DPL-0008/0033: one fenced register
# legalized across the unaligned edge); the row span is the core's own.
set ::lcf_site [[lindex [$::lcf_blk getRows] 0] getSite]
set ::lcf_sw [$::lcf_site getWidth]
set ::lcf_cx [$::lcf_core xMin]
set ::lcf_r [odb::dbRegion_create $::lcf_blk "ctfxs_lane_ctq"]
# s4c: EXCLUSIVE (DEF FENCE): the band holds only the fenced registers.  s4b (default INCLUSIVE) legalized three
# non-member inverters 1 dbu inside the band's right edge (DPL-0006 site alignment, x 165.995 vs edge 165.996).
$::lcf_r setRegionType EXCLUSIVE
set ::lcf_bx0 [expr {$::lcf_cx + int(ceil((round($::lcf_x0*$::lcf_dbu) - $::lcf_cx) / double($::lcf_sw))) * $::lcf_sw}]
set ::lcf_bx1 [expr {$::lcf_cx + int(floor((round($::lcf_x1*$::lcf_dbu) - $::lcf_cx) / double($::lcf_sw))) * $::lcf_sw}]
odb::dbBox_create $::lcf_r $::lcf_bx0 [$::lcf_core yMin] $::lcf_bx1 [$::lcf_core yMax]
set ::lcf_g [odb::dbGroup_create $::lcf_r "ctfxs_lane_ctq_grp"]
set ::lcf_n 0; set ::lcf_a 0.0
foreach i [$::lcf_blk getInsts] {
  set m [$i getMaster]
  if {[$m isBlock] || [$m getType] ne "CORE"} continue
  regsub -all {\\} [$i getName] {} n
  if {![regexp {^u_x[./](u_q[./]|fcl|fvl)} $n]} continue
  if {[$i getGroup] ne "NULL"} continue
  if {[$i isFixed]} continue
  $::lcf_g addInst $i
  incr ::lcf_n
  set ::lcf_a [expr {$::lcf_a + [$m getWidth]*[$m getHeight]/double($::lcf_dbu*$::lcf_dbu)}]
}
set ::lcf_box_a [expr {($::lcf_x1-$::lcf_x0) * ([$::lcf_core yMax]-[$::lcf_core yMin])/double($::lcf_dbu)}]
if {$::lcf_n < 150} { error "CTFXS_LANE_FENCE: only $::lcf_n ctq-replica cells matched (expected >= 150)" }
puts [format "CTFXS_LANE_FENCE cells=%d area=%.1f um2 band=%.1f..%.1f um area=%.1f um2 fill=%.3f" \
  $::lcf_n $::lcf_a $::lcf_x0 $::lcf_x1 $::lcf_box_a [expr {$::lcf_a/$::lcf_box_a}]]
