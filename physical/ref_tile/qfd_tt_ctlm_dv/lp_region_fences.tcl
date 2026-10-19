# lp_region_fences.tcl (MU-DQ-CTLMCLK 10-19, COORD 0ke: ck_core / ck_hr = LOCAL region trees, landed-regions standard)
# qfd_tt_ctlm_dv gate 20261019-044135: TritonCTS saw the ck_core registers spread over a ~560 um sink region (u_gi glue +
# its landing rings pulled east by the hr-side readers), 13-15 buffer levels, boundary spread 177 / 154 ps TT / FF.  A
# landed region is LOCAL by construction, so fence every register of each region root to its own half of the slot:
#   core (ck_core): x 0 .. 432.0   (calendar SRAMs + ROM leaf column, tl pins S x 43.2-410.4, rst_n N x 420.3)
#   hr   (ck_hr):   x 432.0 .. 777.6 (h16c at 475.2, input pin band N x 460-771 / S, outputs, ck_hr S x 655.0)
# Membership = the flop's clock pin net (before CTS each region's registers sit on their port net); combinational cells
# stay free (the placer pulls them to their flops).  INCLUSIVE regions: members must stay inside, others may enter.
# Sourced from pre_gpl.tcl (spec pin_hook_before_flops) after the hold stages, before the pin flops are fixed.
set ot_lrf_block [ord::get_db_block]
set ot_lrf_dbu [$ot_lrf_block getDbUnitsPerMicron]
set ot_lrf_die [$ot_lrf_block getDieArea]
set ot_lrf_split 432.0
set ot_lrf_boxes [dict create ck_core [list 0.0 $ot_lrf_split] ck_hr [list $ot_lrf_split [expr {[$ot_lrf_die xMax] / double($ot_lrf_dbu)}]]]
foreach {ot_lrf_port ot_lrf_x} $ot_lrf_boxes {
  set ot_lrf_bt [$ot_lrf_block findBTerm $ot_lrf_port]
  if {$ot_lrf_bt eq "NULL" || [$ot_lrf_bt getNet] eq "NULL"} { error "OT_LRF: clock port $ot_lrf_port missing" }
  set ot_lrf_net [$ot_lrf_bt getNet]
  set ot_lrf_region [odb::dbRegion_create $ot_lrf_block ot_lrf_$ot_lrf_port]
  $ot_lrf_region setRegionType INCLUSIVE
  lassign $ot_lrf_x ot_lrf_x0 ot_lrf_x1
  odb::dbBox_create $ot_lrf_region [expr {round($ot_lrf_x0 * $ot_lrf_dbu)}] [$ot_lrf_die yMin] \
      [expr {round($ot_lrf_x1 * $ot_lrf_dbu)}] [$ot_lrf_die yMax]
  set ot_lrf_group [odb::dbGroup_create $ot_lrf_region ot_lrf_$ot_lrf_port]
  set ot_lrf_n 0
  foreach ot_lrf_it [$ot_lrf_net getITerms] {
    if {![$ot_lrf_it isInputSignal]} continue
    set ot_lrf_inst [$ot_lrf_it getInst]
    set ot_lrf_m [$ot_lrf_inst getMaster]
    if {[$ot_lrf_m isBlock] || ![$ot_lrf_m isSequential]} continue
    if {[$ot_lrf_inst getGroup] ne "NULL" && [$ot_lrf_inst getGroup] ne ""} { error "OT_LRF: [$ot_lrf_inst getName] already in a group" }
    $ot_lrf_group addInst $ot_lrf_inst
    incr ot_lrf_n
  }
  if {!$ot_lrf_n} { error "OT_LRF: no registers on $ot_lrf_port (region roots must own their flops)" }
  puts [format "OT_LRF region %s x %.1f-%.1f: %d registers fenced" $ot_lrf_port $ot_lrf_x0 $ot_lrf_x1 $ot_lrf_n]
}
