# PRE_CTS hook for the CLAUDE HBM-ABSTRACTS station views (stn_route.sh).  ORFS keeps one PRE_CTS_TCL, so this hook
# first sources the route recipe's own one (the repair_timing buffer cap), then buffers every clock output port that a
# cell drives directly.  A launch slice forwards ck as ck -> kept inverter -> kept inverter -> output port; TritonCTS
# (OpenROAD 26Q3) follows the forwarded clock through both inverters and segfaults in separateMacroRegSinks on a clock
# net whose only load is the block terminal (measured on r1_hfd_meso_r28: crash as built, clean with one buffer on
# the port net).  stn_post_synth.tcl retypes the inout terminals so ORFS port buffering normally puts that buffer
# there already; this hook is the safety net for a forwarding inverter still driving a terminal directly.  The buffer is the
# port driver ORFS would insert anyway; the forwarded clock's polarity and its SDC generated clock at the port are
# unchanged.
source /src/physical/hbm_accel_die_views/stations/bench/stn_repair_capacity.tcl
set ot_blk [ord::get_db_block]
set ot_buf [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
set ot_n 0
foreach ot_bt [$ot_blk getBTerms] {
  if {[$ot_bt getIoType] ni {OUTPUT INOUT}} { continue }
  set ot_net [$ot_bt getNet]
  if {$ot_net eq "NULL" || [$ot_net getSigType] ne "CLOCK"} { continue }
  set ot_its [$ot_net getITerms]
  if {[llength $ot_its] != 1} { continue }
  set ot_drv [lindex $ot_its 0]
  if {![$ot_drv isOutputSignal]} { continue }
  set ot_inst [$ot_drv getInst]
  if {![string match INV* [[$ot_inst getMaster] getName]]} { continue }
  $ot_drv disconnect
  set ot_nn [odb::dbNet_create $ot_blk "ot_fwdport_[incr ot_n]"]
  $ot_nn setSigType CLOCK
  $ot_drv connect $ot_nn
  set ot_b [odb::dbInst_create $ot_blk $ot_buf "ot_fwdport_buf_$ot_n"]
  [$ot_b findITerm A] connect $ot_nn
  [$ot_b findITerm Y] connect $ot_net
  set ot_bb [$ot_inst getBBox]
  $ot_b setLocation [$ot_bb xMin] [$ot_bb yMin]
  $ot_b setPlacementStatus PLACED
  puts "OT_STN: buffered clock output port [$ot_bt getName] (driver [$ot_inst getName])"
}
puts "OT_STN: $ot_n clock output port(s) buffered"
# FENCE=1 (stn_meso_fence.tcl) regions guide placement only: dissolve them before CTS so the clock-inverter clones,
# clock buffers and repair buffers CTS adds are legalised freely (measured r8f45_hfd_cdist_r15: DPL-0033 at CTS with
# the regions kept).  The placed FIFO cells stay where the fenced placement put them.
foreach ot_g [$ot_blk getGroups] {
  if {[string match ot_fence_grp_* [$ot_g getName]]} { odb::dbGroup_destroy $ot_g }
}
foreach ot_r [$ot_blk getRegions] {
  if {[string match ot_fence_* [$ot_r getName]]} {
    puts "OT_STN: dissolve [$ot_r getName] before CTS"
    odb::dbRegion_destroy $ot_r
  }
}
