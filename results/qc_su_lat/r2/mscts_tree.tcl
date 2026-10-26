# mscts_tree.tcl -- QC-SU-LAT-R2 variant T (METHODOLOGY 12.8b): STRUCTURED BINARY CLOCK TREE from the centre entry.
# Sourced AFTER mscts_core.tcl; overrides ot_ms_build only (balance/report/recover work by the ot_ms_* names).
# Root at the island entry -> top node -> recursive binary branch nodes (one buffer per node, fanout 2 per net, every
# leaf at the SAME depth = identical cell chain) -> leaf tap buffers (ot_ms_<LEAF>_clk; TritonCTS builds only the local
# tree under each leaf) -> sinks of the leaf's equal-load region.  Macro clock leaf hangs on the INPUT net of the named leaf
# tap (same depth as that tap) with OT_MSCTS_MACRO_PAD0 fixed cells (same chain per type).  Replaces the v1 star of chains,
# whose root net (16 x ~110 um branches, one 1.8 mm net) cost 75-375 ps by itself (vmr_R2 trunk probe 2026-10-26).
# Spec: set ot_ms_port ck; set ot_ms_root {x y}
#       set ot_ms_tree { {NODE PARENT x y} ... }   (PARENT "root" for the top node; leaves are the ot_ms_taps names)
#       set ot_ms_leaves { {LEAF PARENT {x y} {{rx0 ry0 rx1 ry1}}} ... }   leaf tap buffer at (x y) on PARENT's net
#       set ot_ms_macros { {INST_GLOB LEAF {lx ly}} ... }
proc ot_ms_build {} {
  source $::env(OT_MSCTS_SPEC)
  upvar 0 ot_ms_port port ot_ms_root root ot_ms_leaves leaves ot_ms_macros macros ot_ms_tree tree
  set taps {}; foreach l $leaves { lappend taps [list [lindex $l 0] [lindex $l 2] [lindex $l 3]] }
  set blk [ord::get_db_block]
  if {[$blk findInst ot_ms_root] ne "NULL"} { puts "OT_MSCTS_BUILD already built"; return }
  set ncell [ot_ms_env OT_MSCTS_TRUNK_CELL BUFx16f_ASAP7_75t_R]
  set tapcell [ot_ms_env OT_MSCTS_TAP_CELL BUFx16f_ASAP7_75t_R]
  set rcell [ot_ms_env OT_MSCTS_ROOT_CELL BUFx16f_ASAP7_75t_R]
  set lcell [ot_ms_env OT_MSCTS_LEAF_CELL BUFx8_ASAP7_75t_R]
  set pcell [ot_ms_env OT_MSCTS_PAD_CELL BUFx4_ASAP7_75t_R]
  set bt [$blk findBTerm $port]; set pnet [$bt getNet]
  set sinks {}; set msinks {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal] && [[$it getMTerm] getSigType] ne "CLOCK"} continue
    if {[[[$it getInst] getMaster] isBlock]} { lappend msinks $it } else { lappend sinks $it }
  }
  set ne [ot_ms_env OT_MSCTS_ENTRY_CELLS 0]; set ecell [ot_ms_env OT_MSCTS_ENTRY_CELL BUFx4_ASAP7_75t_R]; set inet $pnet
  lassign $root rx ry
  for {set j 1} {$j <= $ne} {incr j} { set en [ot_ms_mk_net ot_ms_entry${j}_n]; set eb [ot_ms_mk_inst ot_ms_entry$j $ecell [expr {$rx - 1.2 * ($ne - $j + 1)}] $ry]; ot_ms_conn $eb $inet $en; set inet $en }
  set out(root) [ot_ms_mk_net ot_ms_root_n]
  set r [ot_ms_mk_inst ot_ms_root $rcell $rx $ry]; ot_ms_conn $r $inet $out(root)
  # nodes in spec order (parents first)
  foreach nd $tree {
    lassign $nd name par x y
    set out($name) [ot_ms_mk_net ot_ms_${name}_n]
    set b [ot_ms_mk_inst ot_ms_${name}_nd $ncell $x $y]; ot_ms_conn $b $out($par) $out($name)
    set depth($name) [expr {$par eq "root" ? 1 : $depth($par) + 1}]
  }
  set ::ot_ms_tapnets {}; set ::ot_ms_tapinfo {}; set dl {}
  foreach t $taps {
    lassign $t name xy regs; lassign $xy x y
    set par ""; foreach l $leaves { if {[lindex $l 0] eq $name} { set par [lindex $l 1] } }
    set tnet [ot_ms_mk_net ot_ms_${name}_clk]
    set tb [ot_ms_mk_inst ot_ms_${name}_tap $tapcell $x $y]; ot_ms_conn $tb $out($par) $tnet
    lappend ::ot_ms_tapnets ot_ms_${name}_clk
    dict set ::ot_ms_tapinfo $name [list $x $y $regs [$out($par) getName]]
    lappend dl $depth($par)
  }
  if {[llength [lsort -unique $dl]] != 1} { error "OT_MSCTS tree: leaves at different depths [lsort -unique $dl]" }
  set cnt {}
  foreach it $sinks {
    set bb [[$it getInst] getBBox]
    set x [ot_ms_um [expr {([$bb xMin] + [$bb xMax]) / 2}]]; set y [ot_ms_um [expr {([$bb yMin] + [$bb yMax]) / 2}]]
    set tap ""
    foreach t $taps { foreach rr [lindex $t 2] { if {$tap eq "" && [ot_ms_in_rect $x $y $rr]} { set tap [lindex $t 0] } } }
    if {$tap eq ""} { set bd 1e30; dict for {nm inf} $::ot_ms_tapinfo { set d [expr {abs($x - [lindex $inf 0]) + abs($y - [lindex $inf 1])}]; if {$d < $bd} { set bd $d; set tap $nm } }; dict incr cnt "${tap}_nearest" }
    $it disconnect; $it connect [$blk findNet ot_ms_${tap}_clk]
    dict incr cnt $tap
  }
  dict for {k v} $cnt { puts "OT_MSCTS_BUILD sinks $k $v" }
  set pad0 [ot_ms_env OT_MSCTS_MACRO_PAD0 0]; set ::ot_ms_macleaf {}
  foreach it $msinks {
    set inst [$it getInst]; set iname [$inst getName]; set spec ""
    foreach mm $macros { if {[string match [lindex $mm 0] $iname]} { set spec $mm } }
    if {$spec eq ""} { error "OT_MSCTS: macro clock sink $iname has no ot_ms_macros entry" }
    lassign $spec glob tap site; lassign $site lx ly
    set k [llength $::ot_ms_macleaf]
    set prev [$blk findNet [lindex [dict get $::ot_ms_tapinfo $tap] 3]]
    for {set j 0} {$j < $pad0} {incr j} { set n [ot_ms_mk_net ot_ms_m${k}_p$j]; set b [ot_ms_mk_inst ot_ms_m${k}_pad$j $pcell [expr {$lx - 2.0 * ($pad0 - $j)}] $ly]; ot_ms_conn $b $prev $n; set prev $n }
    set ln [ot_ms_mk_net ot_ms_m${k}_clk]
    set lb [ot_ms_mk_inst ot_ms_m${k}_leaf $lcell $lx $ly]; ot_ms_conn $lb $prev $ln
    $it disconnect; $it connect $ln
    lappend ::ot_ms_macleaf [list $iname $tap ot_ms_m${k}_leaf ot_ms_m${k}]
    puts "OT_MSCTS_BUILD macro $iname leaf at ($lx,$ly) on the input net of leaf $tap, $pad0 fixed pad cells"
  }
  ot_ms_protect 1
  puts [format "OT_MSCTS_BUILD tree: %d nodes, %d leaves at depth %d (+root, +tap), root (%.1f, %.1f), %d register sinks, %d macro leaves" [llength $tree] [llength $taps] [lindex $dl 0] $rx $ry [llength $sinks] [llength $::ot_ms_macleaf]]
  if {[info commands ot_ms_cts_orig] eq ""} {
    rename clock_tree_synthesis ot_ms_cts_orig
    proc clock_tree_synthesis {args} {
      set a {}
      for {set i 0} {$i < [llength $args]} {incr i} { if {[lindex $args $i] eq "-clk_nets"} { incr i; continue }; lappend a [lindex $args $i] }
      lappend a -clk_nets $::ot_ms_tapnets
      uplevel 1 [list ot_ms_cts_orig {*}$a]
    }
  }
}
