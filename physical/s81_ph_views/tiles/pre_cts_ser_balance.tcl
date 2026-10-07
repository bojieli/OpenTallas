# CLAUDE S81-PH capture tiles (two related clocks ck 1.2 GHz / ckv 0.9 GHz, ot_ratio_cdc_fifo crossings timed at the
# 278-ps VCO-tick window).  capt_ctl route 1df7cf9a9: core_clk WC insertion 219..292 ps, ser_clk 114..200 ps (the
# serial tree has far fewer sinks): the ~100 ps lead of ser_clk came straight out of the ck -> ckv window
# (mem -> sh -5.8 ps) while the ckv -> ck pointer arcs kept +70 ps.  So, after CTS and before the CTS-stage repair,
# delay the ckv root by BUFx4 stages until the ser_clk mean insertion has closed HALF of the gap to core_clk (both
# crossing directions then share the window; nothing is relaxed, every arc is still timed at 278 ps).  Logic,
# constraints and the clocks are unchanged.  Includes the standard PRE_CTS hook (pre_cts_fclk_root_buf.tcl).
source /src/physical/s81_ph_views/common/pre_cts_fclk_root_buf.tcl
proc ot_lat_mean {clk} {
  sta::redirect_string_begin
  set rc [catch {report_clock_latency -clock $clk -scenes WC}]
  set s [sta::redirect_string_end]
  if {$rc} {
    sta::redirect_string_begin; catch {report_clock_latency -clock $clk}; set s [sta::redirect_string_end]
  }
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} { return [expr {($lo + $hi) / 2.0}] }
  return -1
}
proc ot_ser_balance {} {
  if {[info exists ::ot_ser_bal_done] || [llength [get_clocks -quiet ser_clk]] == 0} { return }
  set ::ot_ser_bal_done 1
  set ck [ot_lat_mean core_clk]; set se [ot_lat_mean ser_clk]
  if {$ck < 0 || $se < 0} { puts "ot_ser_balance: no latency report, unchanged"; return }
  set goal [expr {$se + 0.5 * ($ck - $se)}]
  set blk [ord::get_db_block]
  set bt [$blk findBTerm {ckv[0]}]
  if {$bt eq "NULL"} { set bt [$blk findBTerm ckv] }
  if {$bt eq "NULL"} { error "ot_ser_balance: no ckv port" }
  set mst [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
  # cap: a BUFx4 stage on the root is >= ~15 ps at WC, so never more than (goal - now) / 15 stages even if the
  # latency report were not refreshed after an edit
  set kmax [expr {int(($goal - $se) / 15.0)}]
  set k 0; set now $se
  while {$now < $goal && $k < $kmax} {
    set n [$bt getNet]
    set loads [$n getITerms]
    if {[llength $loads] == 0} { break }
    set b [odb::dbInst_create $blk $mst "ot_ser_bal_buf_$k"]
    set loc [[[lindex $loads 0] getInst] getLocation]
    $b setLocation [lindex $loc 0] [lindex $loc 1]
    $b setPlacementStatus PLACED
    $b setSourceType TIMING
    set nn [odb::dbNet_create $blk "ot_ser_bal_net_$k"]
    $nn setSigType CLOCK
    foreach it $loads { $it disconnect; $it connect $nn }
    [$b findITerm A] connect $n
    [$b findITerm Y] connect $nn
    incr k
    set now [ot_lat_mean ser_clk]
  }
  # dont_touch only once the chain is complete (each new stage re-hangs the previous one's input)
  for {set i 0} {$i < $k} {incr i} { set_dont_touch [get_cells ot_ser_bal_buf_$i] }
  puts "ot_ser_balance: core_clk mean $ck ps, ser_clk mean $se -> $now ps with $k BUFx4 on the ckv root (goal $goal)"
}
if {[info procs repair_timing_helper] ne "" && [info procs ot_s_repair_timing_helper] eq ""} {
  rename repair_timing_helper ot_s_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_ser_balance
    ot_s_repair_timing_helper {*}$args
  }
}
