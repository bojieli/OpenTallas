# ctfn native clock: one compact TritonCTS tree per x quarter of the strip (S-NORM, Claude 2026-10-15; spec pre_cts_extra).
# Measured on s81hc_ctfn_native_ref-np1-75905c4bb (routed TT 192.72 / FF -12.44, worst = input -> pin capture flop):
# ONE root over 5,890 sinks spread along x 70-496 um of a 25.92-um strip -> depth 6-7, TT pin-flop insertion 320-386 ps,
# FF boundary arrival 264.0-327.6 ps (63 ps).  The input-hold reference is the MEDIAN pin flop, so the late end of that
# spread is ~37 ps of extra hold demand at the capture flops; CTS/GRT repair (margin 10) met it before route and the
# routed tree moved it back to -12.44 (ECO pads then broke setup slack and DRC).  A late capture root is the defect.
# Fix: split the clock net into OT_CKS_K (4) equal-count x clusters, one BUFx24 per cluster at its centroid, so CTS
# builds a short local tree per ~145 um quarter (as ctfx_nt: 75 -> 19.5 ps spread).  Same port, clock, flops,
# constraints; one external clock root (the clock rule counts all sinks).
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
