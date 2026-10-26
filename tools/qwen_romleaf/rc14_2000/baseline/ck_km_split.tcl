# QW-CB16R 10-20 (A0 rc12): per-port 2-D k-means local roots for the glue operand roots ck_dw / ck_de (generalises
# physical/common_flow/clock_split_km.tcl, which handles ONE port and is guarded by ot_ckkm_0).
# Why (measured, rc11 CTS rerun with a per-sink dump, results/arch/qw_a0_rc12_1020/ckdump): ck_dw / ck_de sinks form
# 10 separate masses -- the 15-um operand column (L1 ring reads + mq_wrom, 2,728 sinks), the s2_w copies at the hub
# (512) and the eight per-leaf L9 ring writers (381 each beside ck_tx[g]) over 266 x 517 um.  One TritonCTS tree over
# that field left the far column sinks and the far leaf rings 100..270 ps apart (NK dw 124 / de 273, NL dw 191 / de
# 145 ps) although every individual mass is tight (rings 5..30 ps).  Here each port net is split into K compact
# k-means clusters, one BUFx24 local root at each centroid; CTS builds one short tree per cluster under a balanced
# top tree (latency balancing equalises the K roots).  Same ports, clocks, flops, constraints and cycles.
# Knobs (env): OT_CKKM_PORTS ("ck_dw ck_de"), OT_CKKM_K (14), OT_CKKM_ITERS (25).
proc ot_ckkm_split {port K} {
  set ot_ckkm_blk [ord::get_db_block]
  if {[$ot_ckkm_blk findInst ot_ckkm_${port}_0] ne "NULL"} { return }
  set iters [expr {[info exists ::env(OT_CKKM_ITERS)] && $::env(OT_CKKM_ITERS) ne "" ? $::env(OT_CKKM_ITERS) : 25}]
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set bt [$ot_ckkm_blk findBTerm $port]
  if {$bt eq "NULL"} { error "CLOCK_SPLIT_KM: no $port port" }
  set pnet [$bt getNet]
  set xs {}; set ys {}; set its {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    set l [[$it getInst] getLocation]
    lappend xs [expr {[lindex $l 0] / double($u)}]; lappend ys [expr {[lindex $l 1] / double($u)}]; lappend its $it
  }
  set N [llength $its]
  if {$N < 2 * $K} { error "CLOCK_SPLIT_KM: only $N sinks for $K clusters" }
  set mx 0.0; set my 0.0
  foreach x $xs y $ys { set mx [expr {$mx + $x}]; set my [expr {$my + $y}] }
  set mx [expr {$mx / $N}]; set my [expr {$my / $N}]
  # seeds: equal-count groups in angle order around the sink centroid
  set ang {}
  for {set i 0} {$i < $N} {incr i} { lappend ang [list [expr {atan2([lindex $ys $i] - $my, [lindex $xs $i] - $mx)}] $i] }
  set ang [lsort -real -index 0 $ang]
  set cx {}; set cy {}
  for {set k 0} {$k < $K} {incr k} {
    set lo [expr {($N * $k) / $K}]; set hi [expr {($N * ($k + 1)) / $K - 1}]
    set sx 0.0; set sy 0.0
    foreach e [lrange $ang $lo $hi] { set i [lindex $e 1]; set sx [expr {$sx + [lindex $xs $i]}]; set sy [expr {$sy + [lindex $ys $i]}] }
    set n [expr {$hi - $lo + 1}]
    lappend cx [expr {$sx / $n}]; lappend cy [expr {$sy / $n}]
  }
  set asg [lrepeat $N 0]
  for {set r 0} {$r < $iters} {incr r} {
    set moved 0
    for {set i 0} {$i < $N} {incr i} {
      set x [lindex $xs $i]; set y [lindex $ys $i]; set best 0; set bd 1e30
      for {set k 0} {$k < $K} {incr k} {
        set d [expr {abs($x - [lindex $cx $k]) + abs($y - [lindex $cy $k])}]
        if {$d < $bd} { set bd $d; set best $k }
      }
      if {[lindex $asg $i] != $best} { lset asg $i $best; incr moved }
    }
    set sx [lrepeat $K 0.0]; set sy [lrepeat $K 0.0]; set sn [lrepeat $K 0]
    for {set i 0} {$i < $N} {incr i} {
      set k [lindex $asg $i]
      lset sx $k [expr {[lindex $sx $k] + [lindex $xs $i]}]; lset sy $k [expr {[lindex $sy $k] + [lindex $ys $i]}]
      lset sn $k [expr {[lindex $sn $k] + 1}]
    }
    for {set k 0} {$k < $K} {incr k} {
      if {[lindex $sn $k] > 0} { lset cx $k [expr {[lindex $sx $k] / [lindex $sn $k]}]; lset cy $k [expr {[lindex $sy $k] / [lindex $sn $k]}] }
    }
    if {$r > 0 && $moved == 0} break
  }
  set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set nets {}
  for {set k 0} {$k < $K} {incr k} {
    if {[lindex $sn $k] == 0} { lappend nets "" ; continue }
    set b [odb::dbInst_create $ot_ckkm_blk $m ot_ckkm_${port}_$k]
    $b setLocation [expr {int([lindex $cx $k] * $u)}] [expr {int([lindex $cy $k] * $u)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $ot_ckkm_blk ot_ckkm_${port}_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $pnet; [$b findITerm Y] connect $net
    lappend nets $net
  }
  for {set i 0} {$i < $N} {incr i} {
    set it [lindex $its $i]; $it disconnect; $it connect [lindex $nets [lindex $asg $i]]
  }
  array unset ot_ckkm_bx; array unset ot_ckkm_by
  for {set i 0} {$i < $N} {incr i} {
    set k [lindex $asg $i]; lappend ot_ckkm_bx($k) [lindex $xs $i]; lappend ot_ckkm_by($k) [lindex $ys $i]
  }
  for {set k 0} {$k < $K} {incr k} {
    if {[lindex $sn $k] == 0} continue
    set xl [lsort -real $ot_ckkm_bx($k)]; set yl [lsort -real $ot_ckkm_by($k)]
    puts [format "CLOCK_SPLIT_KM: $port cluster %d %d sinks x %.1f..%.1f y %.1f..%.1f buffer at (%.1f, %.1f)" $k [lindex $sn $k] \
      [lindex $xl 0] [lindex $xl end] [lindex $yl 0] [lindex $yl end] [lindex $cx $k] [lindex $cy $k]]
  }
}
set ot_ckkm_ports [expr {[info exists ::env(OT_CKKM_PORTS)] && $::env(OT_CKKM_PORTS) ne "" ? $::env(OT_CKKM_PORTS) : "ck_dw ck_de"}]
set ot_ckkm_k [expr {[info exists ::env(OT_CKKM_K)] && $::env(OT_CKKM_K) ne "" ? $::env(OT_CKKM_K) : 14}]
foreach ot_ckkm_p $ot_ckkm_ports { ot_ckkm_split $ot_ckkm_p $ot_ckkm_k }
detailed_placement
