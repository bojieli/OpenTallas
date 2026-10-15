# FILL-S2 (2026-10-15): serial clock ckv (3:4 to core_clk = ck) of the static layer-die host dsfd_host_c: stage-program outputs t_sseq_pw / t_sseq_plen and sequencer status input f_sseq_st on ckv; same form as physical/s81_fill2/sseq_ser_ref.tcl (from physical/s81_ph_views/gather/gth_ser_ref.tcl).
# the serial clock ser_clk (port ckv, 3:4 to core_clk) of the sp_wfc two-domain blocks.
#   pre_cts   after the clock trees are built and the core boundary is referenced (qwen_die_masters/pre_cts_skew.tcl):
#             (1) ROOT BALANCE: the two trees are built independently, and the ot_ratio_cdc_fifo crossings are timed at the
#             278 ps tick window in both directions, so any difference of the mean insertions comes straight out of one
#             direction's window (S81-PH capt_ctl 1df7cf9a9: 100 ps lead of the serial tree -> mem -> sh -5.8 ps).  The
#             root of the EARLIER tree gets BUFx4 stages until the means meet (nothing relaxed: clocks, constraints and
#             logic unchanged; physical/s81_ph_views/tiles/pre_cts_ser_balance.tcl is the legacy-flow form);
#             (2) the serial ports' boundary re-referenced to the propagated serial tree (gth_ser_ref.sdc).
#   pre_grt   the serial boundary referenced again (io_ref_skew.sdc was just re-read and reset every port to core_clk)
#   post_drt  the plain serial boundary (io_plain.sdc was just read)
set ot_sb_stage [file tail [dict get [info frame -1] file]]
puts "OT_SER hook invoked caller=$ot_sb_stage"
proc ot_ser_lat {clk} {
  sta::redirect_string_begin
  set rc [catch {report_clock_latency -clock $clk}]
  set s [sta::redirect_string_end]
  if {!$rc && [regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $s -> lo hi]} { return [expr {($lo + $hi) / 2.0}] }
  return -1
}
proc ot_ser_port_of {clk} {
  set src [get_property [get_clocks $clk] sources]
  if {[llength $src] != 1} { return "" }
  return [get_full_name [lindex $src 0]]
}
proc ot_ser_balance {} {
  if {[info exists ::ot_ser_bal_done] || ![llength [get_clocks -quiet ser_clk]]} { return }
  set ::ot_ser_bal_done 1
  estimate_parasitics -placement
  set ck [ot_ser_lat core_clk]; set se [ot_ser_lat ser_clk]
  if {$ck < 0 || $se < 0} { puts "OT_SER balance: no latency report, unchanged"; return }
  set early [expr {$se < $ck ? "ser_clk" : "core_clk"}]
  set goal [expr {$se < $ck ? $ck : $se}]; set now [expr {$se < $ck ? $se : $ck}]; set start $now
  set blk [ord::get_db_block]
  set pn [ot_ser_port_of $early]
  set bt [$blk findBTerm $pn]
  if {$bt eq "NULL"} { puts "OT_SER balance: no port for $early ($pn), unchanged"; return }
  set mst [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
  # a BUFx4 stage on the root is >= ~8 ps (parasitics re-estimated after every stage): cap the chain
  set kmax [expr {int(($goal - $now) / 8.0)}]
  set k 0
  set n0 [$bt getNet]
  set n0_dt [$n0 isDoNotTouch]
  if {$n0_dt} { $n0 setDoNotTouch 0 }
  set rel {}
  foreach it [$n0 getITerms] { set i [$it getInst]; if {[$i isDoNotTouch]} { $i setDoNotTouch 0; lappend rel $i } }
  while {$now < $goal - 4.0 && $k < $kmax} {
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
    estimate_parasitics -placement
    set now [ot_ser_lat $early]
  }
  for {set i 0} {$i < $k} {incr i} { set_dont_touch [get_cells ot_ser_bal_buf_$i] }
  foreach i $rel { $i setDoNotTouch 1 }
  if {$n0_dt} {
    $n0 setDoNotTouch 1
    for {set i 0} {$i < $k} {incr i} { [$blk findNet "ot_ser_bal_net_$i"] setDoNotTouch 1 }
  }
  if {$k > 0} { detailed_placement; estimate_parasitics -placement }
  puts "OT_SER balance: core_clk mean $ck ps, ser_clk mean $se ps; $early root delayed $start -> $now ps with $k BUFx4 (goal $goal)"
}
proc ot_ser_boundary {} {
  if {![llength [get_clocks -quiet ser_clk]]} { return }
  set si [get_ports -quiet {f_sseq_st f_sseq_st[*]}]
  set so [get_ports -quiet {t_sseq_pw t_sseq_pw[*] t_sseq_plen t_sseq_plen[*]}]
  set io [expr {0.2 * [get_property [get_clocks ser_clk] period]}]
  if {[llength $si]} { unset_input_delay $si }
  if {[llength $so]} { unset_output_delay $so }
  set ref {}
  if {[info procs ot_pf_ref] ne "" && [llength $si]} { set ref [ot_pf_ref $si] }
  if {[llength $ref]} {
    set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
    set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
    set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
    set hi [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
    puts "OT_SER_BOUNDARY referenced: ser pin flop [get_full_name $ref] arrival max $lmax min $lmin, [llength $si] in / [llength $so] out"
    set_input_delay [expr {$io + $lmax + $sk}] -max -clock ser_clk $si
    set_input_delay [expr {$lmin - $hi}] -min -clock ser_clk $si
    if {[llength $so]} {
      set_output_delay [expr {$io - $lmax + $sk}] -max -clock ser_clk $so
      set_output_delay [expr {0 - $lmin - $hk}] -min -clock ser_clk $so
    }
  } else {
    puts "OT_SER_BOUNDARY plain: [llength $si] in / [llength $so] out at $io ps against ser_clk"
    if {[llength $si]} { set_input_delay $io -clock ser_clk $si }
    if {[llength $so]} { set_output_delay $io -clock ser_clk $so }
  }
}
if {[string match *pre_cts.tcl $ot_sb_stage]} {
  if {[info procs ::ot_sb_cts_orig] eq ""} {
    rename clock_tree_synthesis ::ot_sb_cts_orig
    proc clock_tree_synthesis {args} {
      ::ot_sb_cts_orig {*}$args
      ot_ser_balance
      ot_ser_boundary
    }
  }
} else {
  # pre_grt: io_ref_skew.sdc was just read (ot_pf_ref defined -> referenced); post_drt: io_plain.sdc (-> plain)
  if {[string match *post_drt.tcl $ot_sb_stage]} { catch {rename ot_pf_ref {}} }
  ot_ser_boundary
}
