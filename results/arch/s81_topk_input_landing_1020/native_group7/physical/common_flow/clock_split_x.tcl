# Per-cluster clock roots (S-NORM 2026-10-15): split the clock port net into OT_CKS_K (default 4) equal-count x clusters,
# one BUFx24 local root at each centroid, so CTS builds one short tree per cluster instead of one deep tree over the full
# 576-um span (granted full-span pins put sinks across the whole strip: TT spread 87-132 ps single-root on the gates).
# CTS latency balancing equalises the cluster roots. Same port, clock, flops, constraints; one external clock root.
set ot_cks_blk [ord::get_db_block]
if {[$ot_cks_blk findInst ot_cksplit_0] eq "NULL"} {
  set ot_cks_k [expr {[info exists ::env(OT_CKS_K)] && $::env(OT_CKS_K) ne "" ? $::env(OT_CKS_K) : 4}]
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
  set N [llength $ot_cks_sinks]
  if {$N < 2 * $ot_cks_k} { error "CLOCK_SPLIT: only $N sinks for $ot_cks_k clusters" }
  set ot_cks_m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  for {set k 0} {$k < $ot_cks_k} {incr k} {
    set lo [expr {($N * $k) / $ot_cks_k}]; set hi [expr {($N * ($k + 1)) / $ot_cks_k - 1}]
    set grp [lrange $ot_cks_sinks $lo $hi]
    set sx 0.0; set sy 0.0
    foreach e $grp { set l [[[lindex $e 1] getInst] getLocation]; set sx [expr {$sx + [lindex $l 0]}]; set sy [expr {$sy + [lindex $l 1]}] }
    set n [llength $grp]
    set b [odb::dbInst_create $ot_cks_blk $ot_cks_m ot_cksplit_$k]
    $b setLocation [expr {int($sx / $n)}] [expr {int($sy / $n)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $ot_cks_blk ot_cksplit_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $ot_cks_net; [$b findITerm Y] connect $net
    foreach e $grp { set it [lindex $e 1]; $it disconnect; $it connect $net }
    puts [format "CLOCK_SPLIT: cluster %d %d sinks x %.1f..%.1f buffer at (%.1f, %.1f)" $k $n [lindex $grp 0 0] [lindex $grp end 0] [expr {$sx/$n/$ot_cks_u}] [expr {$sy/$n/$ot_cks_u}]]
  }
  detailed_placement
}
