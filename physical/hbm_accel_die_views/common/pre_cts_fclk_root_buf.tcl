# CLAUDE HBM-ABSTRACTS die views: PRE_CTS hook = the karb repair-buffer-cap hook + a workaround for a TritonCTS crash.
# Die wrappers drive every forwarded-clock output through a kept inverter (ot_fwd_clk_inv) whose input sits on the
# root clock net.  This OpenROAD build segfaults in TritonCTS::separateMacroRegSinks (dbITerm::getInst) when the root
# net carries such non-sink inverter inputs (reproduced on hfd_cmdproc / hfd_loader 3_place.odb; removing the
# inverter loads, or isolating them behind a TIMING-sourced CTS buffer, lets CTS complete).  So: for every inverter
# input on a clock-port net, insert one BUFx24 (the CTS buffer, source TIMING) at the inverter and move the inverter
# onto its output.  CTS then balances that buffer as a sink, so each forwarded clock leaves at leaf insertion delay,
# like the data it accompanies.  Logic, constraints and the clock are unchanged.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
set ot_blk [ord::get_db_block]
set ot_buf [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
set ot_k 0
foreach ot_bt [$ot_blk getBTerms] {
  if {[$ot_bt getIoType] ne "INPUT"} { continue }
  set ot_n [$ot_bt getNet]
  if {$ot_n eq "NULL" || [$ot_n getSigType] ne "CLOCK"} { continue }
  foreach ot_it [$ot_n getITerms] {
    set ot_i [$ot_it getInst]
    if {![string match "INV*" [[$ot_i getMaster] getName]]} { continue }
    set ot_b [odb::dbInst_create $ot_blk $ot_buf "ot_fclk_root_buf_$ot_k"]
    set ot_loc [$ot_i getLocation]
    $ot_b setLocation [lindex $ot_loc 0] [lindex $ot_loc 1]
    $ot_b setPlacementStatus PLACED
    $ot_b setSourceType TIMING
    set ot_nn [odb::dbNet_create $ot_blk "ot_fclk_root_net_$ot_k"]
    $ot_nn setSigType CLOCK
    $ot_it disconnect
    $ot_it connect $ot_nn
    [$ot_b findITerm A] connect $ot_n
    [$ot_b findITerm Y] connect $ot_nn
    incr ot_k
  }
}
puts "pre_cts_fclk_root_buf: $ot_k forwarded-clock inverter(s) isolated behind BUFx24"
if {$ot_k > 0} { detailed_placement }
