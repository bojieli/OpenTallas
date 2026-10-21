# HBM-PVM11 10-21 (PVM9 r10): r9a/r9b 5_1_grt GRT-0116 (overflow 11111 / 9266, avg usage 28%, WL 1.87M vs r8 0.94M).
# Cause: with every kernel net released, 4_1_cts hold repair inserts ~17k buffers on intra-kernel reg->reg nets, but the
# 16 EXCLUSIVE lane fences admit only group members, so the new buffers are legalised OUTSIDE their kernel (DPL
# negotiation stuck at 23540 violations vs 11707 in r8, HPWL +17%) and GRT overflows at the fence/macro-face channels.
# The fences exist to keep kernel-pin nets local at global placement; after 3_place the kernels are placed, so the
# region constraint is dropped here (after the kernel release): cells stay where placed, DPL may legalise CTS/hold
# buffers next to their sinks.  Placement-only change; no cell/net/pin/PG change.
set pf_b [ord::get_db_block]
set pf_ng 0; set pf_nr 0; set pf_ni 0
foreach g [$pf_b getGroups] {
  if {![string match {pvm9_lane*} [$g getName]]} continue
  foreach i [$g getInsts] { $g removeInst $i; incr pf_ni }
  odb::dbGroup_destroy $g; incr pf_ng
}
foreach r [$pf_b getRegions] {
  if {![string match {pvm9_lane*} [$r getName]]} continue
  foreach i [$r getRegionInsts] { $r removeInst $i }
  odb::dbRegion_destroy $r; incr pf_nr
}
puts "PVM11_DROP_FENCES groups=$pf_ng regions=$pf_nr members=$pf_ni"
if {$pf_nr != 16} { error "PVM11_DROP_FENCES expected 16 regions, found $pf_nr" }
