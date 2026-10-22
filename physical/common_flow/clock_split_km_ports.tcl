# Per-region clock roots by 2-D k-means on SEVERAL clock ports (S81-ELEM2-L20RA 2026-10-21).
# clock_split_km.tcl (S81-SLICEP 10-18; closed coll lanes s8ng/s8nh K=24/32) splits ONE port; a multi-root leaf
# (ref_tile clock "multiple_cts_roots", e.g. the Engram lookup dsfd_engram_lkp_ra640: six ck_hash[k] column roots of
# ~5.3k flops each + ck_seed 5.1k) needs the same structural fix on every large root.  Why: s81engm_lkp_ra640c r640c
# gate (b2cf8519d, 10-21) TERMINAL FAIL clock rule: TritonCTS on ck_hash[5] (5312 sinks over a 266 x 94 um region) TT
# spread 106.7 ps > 80 (hash0..4 13.9 / 31.0 / 58.6 / 19.5 / 30.5).  Here each listed port net is split into
# OT_CKKM_K compact sink clusters (Lloyd k-means on placed sink locations, angle-ordered equal-count seeds); one BUFx24
# local root sits at each cluster centroid and CTS builds one short tree per cluster under a balanced top tree to the K
# roots of that port (clock_split_km).  Same ports, clocks, flops, constraints and cycles; each port stays ONE external
# root (the hybrid clock_entries check still sees port -> standard-cell clock pins only).
# Knobs (env): OT_CKKM_PORTS (comma- or space-separated port names, required), OT_CKKM_K (12), OT_CKKM_ITERS (25),
# OT_CKKM_MIN_SINKS (ports with fewer sinks are left to plain CTS; default 4 * K), OT_CKKM_DPL (0 = caller legalises).
# multiple_cts_roots kits (ref_tile forbids pre_cts_extra there) source it via spec pre_dpl_extra with OT_CKKM_DPL=0:
# the split happens on the global placement just before DPL legalises cells + local roots; CTS (4_1) then builds
# the per-cluster trees under each declared port root.
proc ot_ckkm_split_port {blk port K iters tag} {
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set bt [$blk findBTerm $port]
  if {$bt eq "NULL"} { error "CLOCK_SPLIT_KM_PORTS: no port $port" }
  set pnet [$bt getNet]
  set xs {}; set ys {}; set its {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    set l [[$it getInst] getLocation]
    lappend xs [expr {[lindex $l 0] / double($u)}]; lappend ys [expr {[lindex $l 1] / double($u)}]; lappend its $it
  }
  set N [llength $its]
  set minN [expr {[info exists ::env(OT_CKKM_MIN_SINKS)] && $::env(OT_CKKM_MIN_SINKS) ne "" ? $::env(OT_CKKM_MIN_SINKS) : 4 * $K}]
  if {$N < $minN} { puts "CLOCK_SPLIT_KM_PORTS: $port $N sinks < $minN, left to plain CTS"; return 0 }
  set mx 0.0; set my 0.0
  foreach x $xs y $ys { set mx [expr {$mx + $x}]; set my [expr {$my + $y}] }
  set mx [expr {$mx / $N}]; set my [expr {$my / $N}]
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
  set sn [lrepeat $K 0]
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
    if {[lindex $sn $k] == 0} { lappend nets ""; continue }
    set b [odb::dbInst_create $blk $m ot_ckkm_${tag}_$k]
    $b setLocation [expr {int([lindex $cx $k] * $u)}] [expr {int([lindex $cy $k] * $u)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $blk ot_ckkm_${tag}_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $pnet; [$b findITerm Y] connect $net
    lappend nets $net
  }
  for {set i 0} {$i < $N} {incr i} {
    set it [lindex $its $i]; $it disconnect; $it connect [lindex $nets [lindex $asg $i]]
  }
  array set bx {}; array set by {}
  for {set i 0} {$i < $N} {incr i} {
    set k [lindex $asg $i]; lappend bx($k) [lindex $xs $i]; lappend by($k) [lindex $ys $i]
  }
  for {set k 0} {$k < $K} {incr k} {
    if {[lindex $sn $k] == 0} continue
    set xl [lsort -real $bx($k)]; set yl [lsort -real $by($k)]
    puts [format "CLOCK_SPLIT_KM_PORTS: %s cluster %d %d sinks x %.1f..%.1f y %.1f..%.1f buffer at (%.1f, %.1f)" $port $k \
      [lindex $sn $k] [lindex $xl 0] [lindex $xl end] [lindex $yl 0] [lindex $yl end] [lindex $cx $k] [lindex $cy $k]]
  }
  return 1
}
set ot_ckkmp_blk [ord::get_db_block]
if {[$ot_ckkmp_blk findInst ot_ckkm_p0_0] eq "NULL"} {
  if {![info exists ::env(OT_CKKM_PORTS)] || [string trim $::env(OT_CKKM_PORTS)] eq ""} { error "CLOCK_SPLIT_KM_PORTS: OT_CKKM_PORTS unset" }
  set ot_ckkmp_K [expr {[info exists ::env(OT_CKKM_K)] && $::env(OT_CKKM_K) ne "" ? $::env(OT_CKKM_K) : 12}]
  set ot_ckkmp_it [expr {[info exists ::env(OT_CKKM_ITERS)] && $::env(OT_CKKM_ITERS) ne "" ? $::env(OT_CKKM_ITERS) : 25}]
  set ot_ckkmp_i 0; set ot_ckkmp_n 0
  foreach ot_ckkmp_port [split [string trim [string map {, " "} $::env(OT_CKKM_PORTS)]]] {
    if {$ot_ckkmp_port eq ""} continue
    incr ot_ckkmp_n [ot_ckkm_split_port $ot_ckkmp_blk $ot_ckkmp_port $ot_ckkmp_K $ot_ckkmp_it p$ot_ckkmp_i]
    incr ot_ckkmp_i
  }
  puts "CLOCK_SPLIT_KM_PORTS: $ot_ckkmp_n of $ot_ckkmp_i ports split into K=$ot_ckkmp_K regional roots"
  # As a pre_dpl_extra hook (ORFS 3_5 runs detailed_placement right after its PRE_DETAIL_PLACE hook) set
  # OT_CKKM_DPL=0; as a pre_cts hook (default) legalise the new local roots here, as clock_split_km does.
  if {!([info exists ::env(OT_CKKM_DPL)] && $::env(OT_CKKM_DPL) eq "0")} { detailed_placement }
}
