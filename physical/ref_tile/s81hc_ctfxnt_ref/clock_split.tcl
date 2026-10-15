# ctfx_nt clock: one TritonCTS tree per sink cluster (S-NORM, Claude 2026-10-14 23:20; spec pre_cts_extra).
# The strip's registers sit in two disjoint x clusters fixed by die pins: the NORM lanes (dl/ul/cs, x 40-86) and the
# data capture/launch rows (fd_in/fdx, x 227-342).  One H-tree over their joint box puts its level-3/4 buffers in the
# empty gap (x ~110-183) and strings leaf nets 70-85 um back to the data rows: leaf stages 55 ps slower, TT spread
# 66 ps, native capture S+R up to 211 ps.  Splitting the clock net at the 1-D two-means cut of sink x into one BUFx24 per cluster
# (at the cluster centroid) lets CTS build a compact tree per cluster: measured on the 22:27 gate placement 75 -> 38 ps
# (lanes 278-291, data 294-316).  Same port, clock, flops, constraints; one root (clock rule counts all sinks).
set ot_cks_blk [ord::get_db_block]
if {[$ot_cks_blk findInst ot_cksplit_0] eq "NULL"} {
  set ot_cks_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set ot_cks_bt [$ot_cks_blk findBTerm clk]
  if {$ot_cks_bt eq "NULL"} { error "CLOCK_SPLIT: no clk port" }
  set ot_cks_net [$ot_cks_bt getNet]
  set ot_cks_sinks {}
  foreach it [$ot_cks_net getITerms] {
    if {![$it isInputSignal]} continue
    lappend ot_cks_sinks [list [expr {[lindex [[$it getInst] getLocation] 0] / double($ot_cks_u)}] $it]
  }
  set ot_cks_sinks [lsort -real -index 0 $ot_cks_sinks]
  # 1-D two-means on sink x (minimum within-cluster sum of squares over every sorted cut)
  set N [llength $ot_cks_sinks]; set S 0.0; set Q 0.0
  foreach e $ot_cks_sinks { set x [lindex $e 0]; set S [expr {$S + $x}]; set Q [expr {$Q + $x*$x}] }
  set ls 0.0; set lq 0.0; set best 1e30; set ot_cks_cut 0
  for {set i 1} {$i < $N} {incr i} {
    set x [lindex $ot_cks_sinks [expr {$i-1}] 0]; set ls [expr {$ls + $x}]; set lq [expr {$lq + $x*$x}]
    set rs [expr {$S - $ls}]; set rq [expr {$Q - $lq}]
    set sse [expr {($lq - $ls*$ls/$i) + ($rq - $rs*$rs/($N-$i))}]
    if {$sse < $best} { set best $sse; set ot_cks_cut $i }
  }
  set ot_cks_groups [list [lrange $ot_cks_sinks 0 [expr {$ot_cks_cut-1}]] [lrange $ot_cks_sinks $ot_cks_cut end]]
  set ot_cks_gap [expr {[lindex $ot_cks_sinks $ot_cks_cut 0] - [lindex $ot_cks_sinks [expr {$ot_cks_cut-1}] 0]}]
  set ot_cks_m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set k 0
  foreach grp $ot_cks_groups {
    set sx 0.0; set sy 0.0
    foreach e $grp { set l [[[lindex $e 1] getInst] getLocation]; set sx [expr {$sx + [lindex $l 0]}]; set sy [expr {$sy + [lindex $l 1]}] }
    set n [llength $grp]
    set b [odb::dbInst_create $ot_cks_blk $ot_cks_m ot_cksplit_$k]
    $b setLocation [expr {int($sx / $n)}] [expr {int($sy / $n)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $ot_cks_blk ot_cksplit_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $ot_cks_net; [$b findITerm Y] connect $net
    foreach e $grp { set it [lindex $e 1]; $it disconnect; $it connect $net }
    puts [format "CLOCK_SPLIT: cluster %d %d sinks x %.1f..%.1f buffer at (%.1f, %.1f)" $k $n [lindex $grp 0 0] [lindex $grp end 0] [expr {$sx/$n/$ot_cks_u}] [expr {$sy/$n/$ot_cks_u}]]
    incr k
  }
  detailed_placement
  puts [format "CLOCK_SPLIT: two-means cut at sink %d of %d, local gap %.1f um" $ot_cks_cut $N $ot_cks_gap]
}
