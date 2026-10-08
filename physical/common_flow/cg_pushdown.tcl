# CLAUDE setup-triage 2026-10-07: clock-gate push-down (ICG cloning) before CTS.
#
# Triage (claude-takeover-20261007/setup-triage.md, class A): every half-rate clock gater in the failing set sits as ONE
# gate at the root of a deep gated subtree (CTS balances the ungated leaves to that subtree, ~900-1000 ps below the gate),
# so the gate's enable -- launched by a register on a balanced leaf -- arrives ~T after the gate's own clock pin:
#   vred_slice64_c12h  u_g/en_l -> u_g AND   latch 1212 vs gate 170  -899 ps
#   vred_top1024_c12h  same                  1336 vs 326             -879 ps
#   hfd_loader half    hen_h_l -> AND        760 vs 123              -604 ps
#   s81 BF recut       u_z -> u_icg/ENA      1032 vs 301             -330 ps
#   selt_c half        hen_l -> AND          943 vs 133+T/2          -154 ps
#   w2-rb HALF NO2/3   gater on a LEAF; gated tree stacked below it  -405 / -373 ps
# Standard remedy (what commercial CTS does with ICG cloning): replace one root gate by one gate PER SINK CLUSTER, placed
# at the cluster, all sharing the same enable net.  Each clone's clock pin then sits near the leaf level of the ungated
# tree, i.e. at about the arrival of the register that launches the enable, and the gated subtree below a clone is
# shallow.  Function is unchanged: every clone computes the same clk & en_l (or ICG(clk, ENA)) for a subset of the same
# sinks; the enable net and the latch / ICG cell type are untouched; STA times the real result.
#
# Runs as an ORFS PRE_CTS hook (wraps clock_tree_synthesis; the clones are placed at their cluster centroid and the
# post-CTS detailed_placement in cts.tcl legalizes them).  Gates handled: ICG* cells (CLK / ENA [/ SE] -> GCLK), and
# hand-built 2-input AND gates whose one input net carries a clock (a clock-port net or a net that clocks registers)
# and whose output net clocks >= OT_CG_MIN registers.  Knobs: OT_CG_K (sinks per clone, default 48), OT_CG_MIN (64).
# Fails closed (error) if a moved sink is not a register clock pin.
proc ot_cg_is_seq {m} { return [regexp {^(DFF|DHL|DLL|SDF|ICG|ASYNC_DFF)} [$m getName]] }
proc ot_cg_clk_sinks {net} {
  set s {}
  foreach it [$net getITerms] {
    if {[$it isInputSignal] && [ot_cg_is_seq [[$it getInst] getMaster]] && [[$it getMTerm] getName] in {CLK clk}} { lappend s $it }
  }
  return $s
}
proc ot_cg_is_clock_net {net} {
  if {$net eq "NULL"} { return 0 }
  foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT" && [$net getSigType] eq "CLOCK"} { return 1 } }
  if {[llength [ot_cg_clk_sinks $net]] > 0} { return 1 }
  # a clock-port net feeding only through a kept root buffer
  set drv [$net getFirstOutput]
  if {$drv ne "NULL" && $drv ne ""} {
    set di [$drv getInst]
    if {[string match "BUF*" [[$di getMaster] getName]]} {
      set in [$di findITerm A]
      if {$in ne "NULL"} { set n2 [$in getNet]; if {$n2 ne "NULL" && [$n2 getSigType] eq "CLOCK"} { return 1 } }
    }
  }
  return 0
}
# recursive median bisection of iterm list into clusters of <= K
proc ot_cg_split {its K} {
  if {[llength $its] <= $K} { return [list $its] }
  set xs {}; set ys {}
  foreach it $its { lassign [[$it getInst] getLocation] x y; lappend xs $x; lappend ys $y }
  set dx [expr {[tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs]}]
  set dy [expr {[tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys]}]
  set idx [expr {$dx >= $dy ? 0 : 1}]
  set keyed {}
  foreach it $its { lassign [[$it getInst] getLocation] x y; lappend keyed [list [expr {$idx == 0 ? $x : $y}] $it] }
  set keyed [lsort -integer -index 0 $keyed]
  set h [expr {[llength $keyed] / 2}]
  set a {}; set b {}
  foreach e [lrange $keyed 0 [expr {$h-1}]] { lappend a [lindex $e 1] }
  foreach e [lrange $keyed $h end] { lappend b [lindex $e 1] }
  return [concat [ot_cg_split $a $K] [ot_cg_split $b $K]]
}
set ::ot_cg_clones 0
proc ot_cg_pushdown {} {
  set K [expr {[info exists ::env(OT_CG_K)] ? $::env(OT_CG_K) : 48}]
  set MIN [expr {[info exists ::env(OT_CG_MIN)] ? $::env(OT_CG_MIN) : 64}]
  set blk [ord::get_db_block]
  set gates {}
  foreach inst [$blk getInsts] {
    set m [$inst getMaster]; set mn [$m getName]
    if {[string match "ICG*" $mn]} {
      set ck [$inst findITerm CLK]; set out [$inst findITerm GCLK]
      if {$ck eq "NULL" || $out eq "NULL"} continue
      lappend gates [list $inst CLK GCLK]
    } elseif {[regexp {^AND2x} $mn]} {
      set out [$inst findITerm Y]; if {$out eq "NULL"} continue
      set on [$out getNet]; if {$on eq "NULL"} continue
      if {[llength [ot_cg_clk_sinks $on]] < $MIN} continue
      set ckpin ""
      foreach p {A B} {
        set it [$inst findITerm $p]; if {$it eq "NULL"} continue
        if {[ot_cg_is_clock_net [$it getNet]]} { set ckpin $p; break }
      }
      if {$ckpin eq ""} continue
      lappend gates [list $inst $ckpin Y]
      # hand-built gater: the enable pin's driver is the gating latch / negedge flop when it is sequential and feeds
      # only this gate; it is cloned with the gate so latch -> AND stays local (as inside an ICG cell)
      set enpin [expr {$ckpin eq "A" ? "B" : "A"}]
      set ::ot_cg_latch([$inst getName]) ""
      set en [[$inst findITerm $enpin] getNet]
      if {$en ne "NULL"} {
        set d [$en getFirstOutput]
        if {$d ne "NULL" && $d ne "" && [llength [$en getITerms]] == 2} {
          set li [$d getInst]
          if {[ot_cg_is_seq [$li getMaster]]} { set ::ot_cg_latch([$inst getName]) [list $li [[$d getMTerm] getName] $enpin] }
        }
      }
    }
  }
  set total 0
  foreach g $gates {
    lassign $g inst ckp outp
    set out [$inst findITerm $outp]; set gnet [$out getNet]
    if {$gnet eq "NULL"} continue
    set sinks [ot_cg_clk_sinks $gnet]
    set others [expr {[llength [$gnet getITerms]] - 1 - [llength $sinks]}]
    if {[llength $sinks] < $MIN} continue
    set clusters [ot_cg_split $sinks $K]
    set m [$inst getMaster]
    set k 0
    foreach cl [lrange $clusters 1 end] {
      incr k
      set cname "[string map {/ _} [$inst getName]]_cgpd$k"
      set c [odb::dbInst_create $blk $m $cname]
      foreach mt [$m getMTerms] {
        set pn [$mt getName]
        if {$pn eq $outp} continue
        set src [$inst findITerm $pn]
        if {$src eq "NULL"} continue
        set n [$src getNet]
        if {$n ne "NULL"} { [$c findITerm $pn] connect $n }
      }
      if {[info exists ::ot_cg_latch([$inst getName])] && $::ot_cg_latch([$inst getName]) ne ""} {
        lassign $::ot_cg_latch([$inst getName]) li lq enpin
        set lm [$li getMaster]
        set lc [odb::dbInst_create $blk $lm "[string map {/ _} [$li getName]]_cgpd$k"]
        foreach mt [$lm getMTerms] {
          set pn [$mt getName]
          if {$pn eq $lq} continue
          set src [$li findITerm $pn]
          if {$src eq "NULL"} continue
          set n [$src getNet]
          if {$n ne "NULL"} { [$lc findITerm $pn] connect $n }
        }
        set ln [odb::dbNet_create $blk "[string map {/ _} [$li getName]]_cgpd${k}_q"]
        [$lc findITerm $lq] connect $ln
        [$c findITerm $enpin] disconnect
        [$c findITerm $enpin] connect $ln
        set ::ot_cg_newlatch($cname) $lc
      }
      set nn [odb::dbNet_create $blk "[string map {/ _} [$gnet getName]]_cgpd$k"]
      $nn setSigType CLOCK
      [$c findITerm $outp] connect $nn
      set sx 0; set sy 0
      foreach it $cl {
        lassign [[$it getInst] getLocation] x y; incr sx $x; incr sy $y
        $it disconnect; $it connect $nn
      }
      set n [llength $cl]
      $c setLocation [expr {$sx / $n}] [expr {$sy / $n}]
      $c setPlacementStatus PLACED
      if {[info exists ::ot_cg_newlatch($cname)]} { set lc $::ot_cg_newlatch($cname); $lc setLocation [expr {$sx / $n}] [expr {$sy / $n}]; $lc setPlacementStatus PLACED }
    }
    # re-centre the original gate on its own (first) cluster
    set cl [lindex $clusters 0]; set sx 0; set sy 0
    foreach it $cl { lassign [[$it getInst] getLocation] x y; incr sx $x; incr sy $y }
    if {![$inst isFixed]} { $inst setLocation [expr {$sx / [llength $cl]}] [expr {$sy / [llength $cl]}]; $inst setPlacementStatus PLACED }
    set lat [expr {[info exists ::ot_cg_latch([$inst getName])] && $::ot_cg_latch([$inst getName]) ne "" ? [[lindex $::ot_cg_latch([$inst getName]) 0] getName] : "-"}]
    if {$lat ne "-"} { set li [lindex $::ot_cg_latch([$inst getName]) 0]; if {![$li isFixed]} { $li setLocation [expr {$sx / [llength $cl]}] [expr {$sy / [llength $cl]}]; $li setPlacementStatus PLACED } }
    puts "OT_CG_PUSHDOWN latch=$lat [$inst getName] ([$m getName]) sinks=[llength $sinks] other_loads=$others clusters=[llength $clusters] clones=$k"
    incr total $k
  }
  puts "OT_CG_PUSHDOWN total gates=[llength $gates] clones=$total K=$K MIN=$MIN"
  set ::ot_cg_clones $total
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_cgpd_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_cgpd_cts_orig
  proc clock_tree_synthesis {args} {
    ot_cg_pushdown
    # the shared enable net now fans out to every clone: buffer it (and only new DRV violations) before the tree
    # is built, as placement-stage repair_design would have
    if {$::ot_cg_clones > 0} { estimate_parasitics -placement; repair_design }
    ot_cgpd_cts_orig {*}$args
  }
}
