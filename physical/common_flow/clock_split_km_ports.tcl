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
# LEAF LEVEL (COLLB-RA640 2026-10-21): the ra640k/l/m gates (K=12/20/16) FAILED the clock rule (TT spread 152.8 / 97.6
# / 95.4 ps) because the hybrid CTS (clock_entries.tcl, TritonCTS -clk_nets = declared port roots only) built H-trees
# over the K BUFx24 local roots and NOTHING below them: each ot_ckkm cluster net drove 78-406 flops unbuffered.  With
# OT_CKKM_LEAF=G (>0) every cluster is further cut by recursive median bisection (longer axis first, equal counts)
# into ceil(n/G)-ish compact leaf groups of <= G sinks, one OT_CKKM_LEAF_CELL (BUFx12f) leaf buffer at each group
# centroid driven by the cluster root: port -> CTS top tree -> BUFx24 regional root -> leaf buffer -> <= G flops.
# OT_CKKM_L1=kd replaces the level-1 k-means by the same equal-count bisection (all regional roots carry n/K sinks).
# Knobs (env): OT_CKKM_PORTS (comma- or space-separated port names, required), OT_CKKM_K (12), OT_CKKM_ITERS (25),
# OT_CKKM_MIN_SINKS (ports with fewer sinks are left to plain CTS; default 4 * K), OT_CKKM_DPL (0 = caller legalises).
# multiple_cts_roots kits (ref_tile forbids pre_cts_extra there) source it via spec pre_dpl_extra with OT_CKKM_DPL=0:
# the split happens on the global placement just before DPL legalises cells + local roots; CTS (4_1) then builds
# the per-cluster trees under each declared port root.
proc ot_ckkm_kd {idx xs ys K} {
  # Recursive median bisection of the index list idx into K groups (counts proportional to the K split).
  if {$K <= 1 || [llength $idx] <= 1} { return [list $idx] }
  set xl {}; set yl {}
  foreach i $idx { lappend xl [lindex $xs $i]; lappend yl [lindex $ys $i] }
  set xs_ [lsort -real $xl]; set ys_ [lsort -real $yl]
  if {([lindex $xs_ end] - [lindex $xs_ 0]) >= ([lindex $ys_ end] - [lindex $ys_ 0])} { set ax $xs } else { set ax $ys }
  set srt {}
  foreach i $idx { lappend srt [list [lindex $ax $i] $i] }
  set srt [lsort -real -index 0 $srt]
  set Ka [expr {$K / 2}]; set Kb [expr {$K - $Ka}]
  set na [expr {int(round([llength $idx] * double($Ka) / $K))}]
  set a {}; set b {}
  set j 0
  foreach e $srt { if {$j < $na} { lappend a [lindex $e 1] } else { lappend b [lindex $e 1] }; incr j }
  return [concat [ot_ckkm_kd $a $xs $ys $Ka] [ot_ckkm_kd $b $xs $ys $Kb]]
}
proc ot_ckkm_leaf {blk u net its xs ys G tag} {
  # Cut one regional cluster (sinks its at xs/ys, now on net) into leaf groups of <= G sinks, one leaf buffer each.
  set n [llength $its]
  if {$G <= 0 || $n <= $G} { return 0 }
  set L [expr {($n + $G - 1) / $G}]
  set idx {}; for {set i 0} {$i < $n} {incr i} { lappend idx $i }
  set cell [expr {[info exists ::env(OT_CKKM_LEAF_CELL)] && $::env(OT_CKKM_LEAF_CELL) ne "" ? $::env(OT_CKKM_LEAF_CELL) : "BUFx12f_ASAP7_75t_R"}]
  set m [[ord::get_db] findMaster $cell]
  if {$m eq "NULL"} { error "CLOCK_SPLIT_KM_PORTS: no leaf master $cell" }
  set g 0; set mx 0; set mn 1000000
  foreach grp [ot_ckkm_kd $idx $xs $ys $L] {
    if {![llength $grp]} continue
    set sx 0.0; set sy 0.0
    foreach i $grp { set sx [expr {$sx + [lindex $xs $i]}]; set sy [expr {$sy + [lindex $ys $i]}] }
    set k [llength $grp]
    set b [odb::dbInst_create $blk $m ${tag}_l$g]
    $b setLocation [expr {int($sx / $k * $u)}] [expr {int($sy / $k * $u)}]; $b setPlacementStatus PLACED
    set ln [odb::dbNet_create $blk ${tag}_l${g}_clk]; $ln setSigType CLOCK
    [$b findITerm A] connect $net; [$b findITerm Y] connect $ln
    foreach i $grp { set it [lindex $its $i]; $it disconnect; $it connect $ln }
    if {$k > $mx} { set mx $k }; if {$k < $mn} { set mn $k }
    incr g
  }
  return [list $g $mn $mx]
}
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
  set l1 [expr {[info exists ::env(OT_CKKM_L1)] && $::env(OT_CKKM_L1) ne "" ? $::env(OT_CKKM_L1) : "km"}]
  if {$l1 eq "kd"} { set iters 0 }
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
  if {$l1 eq "kd"} {
    set idx {}; for {set i 0} {$i < $N} {incr i} { lappend idx $i }
    set asg [lrepeat $N 0]; set cx {}; set cy {}; set sn {}
    set k 0
    foreach grp [ot_ckkm_kd $idx $xs $ys $K] {
      set sx 0.0; set sy 0.0
      foreach i $grp { lset asg $i $k; set sx [expr {$sx + [lindex $xs $i]}]; set sy [expr {$sy + [lindex $ys $i]}] }
      set c [llength $grp]
      lappend sn $c; lappend cx [expr {$c ? $sx / $c : 0.0}]; lappend cy [expr {$c ? $sy / $c : 0.0}]
      incr k
    }
  } elseif {$l1 ne "km"} { error "CLOCK_SPLIT_KM_PORTS: OT_CKKM_L1=$l1 (km|kd)" }
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
  set G [expr {[info exists ::env(OT_CKKM_LEAF)] && $::env(OT_CKKM_LEAF) ne "" ? $::env(OT_CKKM_LEAF) : 0}]
  if {$G > 0} {
    set nl 0; set gmn 1000000; set gmx 0
    for {set k 0} {$k < $K} {incr k} {
      if {[lindex $sn $k] == 0} continue
      set cits {}; set cxs {}; set cys {}
      for {set i 0} {$i < $N} {incr i} {
        if {[lindex $asg $i] == $k} { lappend cits [lindex $its $i]; lappend cxs [lindex $xs $i]; lappend cys [lindex $ys $i] }
      }
      set r [ot_ckkm_leaf $blk $u [lindex $nets $k] $cits $cxs $cys $G ot_ckkm_${tag}_$k]
      if {$r ne 0} {
        incr nl [lindex $r 0]
        if {[lindex $r 1] < $gmn} { set gmn [lindex $r 1] }; if {[lindex $r 2] > $gmx} { set gmx [lindex $r 2] }
      }
    }
    puts "CLOCK_SPLIT_KM_PORTS: $port leaf level G=$G: $nl leaf buffers, $gmn..$gmx sinks per leaf"
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
