# mscts_h.tcl -- QC-SU-LAT-R3 (METHODOLOGY 12.8b/c/d1): fully plan-built internal H-tree.  Sourced AFTER mscts_core.tcl;
# overrides ot_ms_build only.  Spec (mkspec_h.py): ot_ms_root, ot_h_entry_n, ot_h_fixed, ot_ms_tree {NODE PARENT x y CELL},
# ot_ms_leaves {LEAF PARENT {x y} {} CELL}, ot_ms_macros {GLOB LEAF {x y}}.
# ck -> entry chain (fixed) -> root -> M legs -> Q leaf-island drivers (fixed) -> B -> S -> leaf drivers -> registers;
# macro clock pin: one leaf driver (same cell + depth as the register leaves) on the S net (input net of LEAF).
# Instances that pushdown.tcl created FIRM (ot_h_fixed) are reused in place.  No TritonCTS (OT_H_NO_TRITON=1), no pads.
proc ot_h_inst {name master x y} {
  set i [[ord::get_db_block] findInst $name]
  if {$i ne "NULL"} {
    foreach it [$i getITerms] { if {[[$it getMTerm] getSigType] ni {POWER GROUND} && [$it getNet] ne "NULL"} { $it disconnect } }
    return $i
  }
  return [ot_ms_mk_inst $name $master $x $y]
}
proc ot_ms_build {} {
  source $::env(OT_MSCTS_SPEC)
  upvar 0 ot_ms_port port ot_ms_root root ot_ms_leaves leaves ot_ms_macros macros ot_ms_tree tree ot_h_entry_n ne ot_h_fixed fixed
  set blk [ord::get_db_block]
  if {[$blk findNet ot_ms_root_n] ne "NULL"} { puts "OT_MSCTS_BUILD already built"; return }
  set rcell BUFx24_ASAP7_75t_R; set ecell BUFx16f_ASAP7_75t_R
  set bt [$blk findBTerm $port]; set pnet [$bt getNet]
  set sinks {}; set msinks {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal] && [[$it getMTerm] getSigType] ne "CLOCK"} continue
    if {[[[$it getInst] getMaster] isBlock]} { lappend msinks $it } else { lappend sinks $it }
  }
  set inet $pnet
  for {set j 1} {$j <= $ne} {incr j} { set en [ot_ms_mk_net ot_ms_entry${j}_n]; set eb [ot_h_inst ot_ms_entry$j $ecell 0 0]; ot_ms_conn $eb $inet $en; set inet $en }
  set out(root) [ot_ms_mk_net ot_ms_root_n]
  set r [ot_h_inst ot_ms_root $rcell {*}$root]; ot_ms_conn $r $inet $out(root)
  foreach nd $tree {
    lassign $nd name par x y cell
    set out($name) [ot_ms_mk_net ot_ms_${name}_n]
    set b [ot_h_inst ot_ms_${name}_nd $cell $x $y]; ot_ms_conn $b $out($par) $out($name)
    set depth($name) [expr {$par eq "root" ? 1 : $depth($par) + 1}]
  }
  set ::ot_ms_tapnets {}; set ::ot_ms_tapinfo {}; set dl {}
  foreach l $leaves {
    lassign $l name par xy regs cell; lassign $xy x y
    set tnet [ot_ms_mk_net ot_ms_${name}_clk]
    set tb [ot_h_inst ot_ms_${name}_tap $cell $x $y]; ot_ms_conn $tb $out($par) $tnet
    lappend ::ot_ms_tapnets ot_ms_${name}_clk
    dict set ::ot_ms_tapinfo $name [list $x $y $regs [$out($par) getName]]
    lappend dl $depth($par)
  }
  if {[llength [lsort -unique $dl]] != 1} { error "OT_MSCTS H: leaves at different depths [lsort -unique $dl]" }
  # Frozen named membership from the pre-CTS plan, never nearest-leaf reassignment.
  set actual {}; foreach it $sinks { dict set actual [list [[$it getInst] getName] [[$it getMTerm] getName]] $it }
  set used {}; set cnt {}
  foreach leaf $leaves {
    lassign $leaf name par xy regs cell
    if {![llength $regs]} { error "R4 empty planned leaf $name" }
    foreach key $regs {
      set key [list {*}$key]
      if {![dict exists $actual $key]} { error "R4 missing planned clock sink $key" }
      if {[dict exists $used $key]} { error "R4 duplicate planned clock sink $key" }
      dict set used $key 1; set it [dict get $actual $key]
      $it disconnect; $it connect [$blk findNet ot_ms_${name}_clk]
      dict incr cnt $name
    }
  }
  if {[dict size $actual] != [dict size $used]} { error "R4 uncovered sinks [dict size $actual] vs [dict size $used]" }
  set counts [dict values $cnt]
  puts "OT_R4_MEMBERSHIP sinks [dict size $used] leaves [dict size $cnt] load [lindex [lsort -integer $counts] 0]..[lindex [lsort -integer $counts] end]"
  set ::ot_ms_macleaf {}
  foreach it $msinks {
    set inst [$it getInst]; set iname [$inst getName]; set spec ""
    foreach mm $macros { if {[lindex $mm 0] eq $iname} { set spec $mm } }
    if {$spec eq ""} { error "OT_MSCTS: macro clock sink $iname has no ot_ms_macros entry" }
    lassign $spec glob tap site; lassign $site mx_ my_
    set lcell ""; foreach l $leaves { if {[lindex $l 0] eq $tap} { set lcell [lindex $l 4] } }
    set k [llength $::ot_ms_macleaf]
    set prev [$blk findNet [lindex [dict get $::ot_ms_tapinfo $tap] 3]]
    set ln [ot_ms_mk_net ot_ms_m${k}_clk]
    set lb [ot_ms_mk_inst ot_ms_m${k}_leaf $lcell $mx_ $my_]; ot_ms_conn $lb $prev $ln
    $it disconnect; $it connect $ln
    lappend ::ot_ms_macleaf [list $iname $tap ot_ms_m${k}_leaf ot_ms_m${k}]
    puts "OT_MSCTS_BUILD macro $iname designed leaf stage $lcell at ($mx_,$my_) on the S net of leaf $tap (same depth as register leaves)"
  }
  set _pd {}; foreach i [$blk getInsts] {
    if {[string match "ot_ms_*" [$i getName]] || [string match "ot_isl_*" [$i getName]]} {
      lappend _pd $i; $i setDoNotTouch 0
    }
  }
  global_connect
  foreach i $_pd {
    foreach it [$i getITerms] {
      set sig [[$it getMTerm] getSigType]
      if {$sig ni {POWER GROUND}} continue
      if {[$it getNet] eq "NULL" || [[ $it getNet] getSigType] ne $sig} { error "R4 unbound PG [$i getName]/[[$it getMTerm] getName]" }
    }
  }
  ot_ms_protect 1
  foreach i $_pd { $i setDoNotTouch 1 }
  puts [format "OT_MSCTS_BUILD H-tree: entry chain %d, %d nodes, %d leaves at depth %d, %d register sinks, %d macro leaves" $ne [llength $tree] [llength $leaves] [lindex $dl 0] [llength $sinks] [llength $::ot_ms_macleaf]]
  if {[info commands ot_ms_cts_orig] eq ""} {
    rename clock_tree_synthesis ot_ms_cts_orig
    proc clock_tree_synthesis {args} {
      if {[ot_ms_env OT_H_NO_TRITON 0]} { puts "OT_MSCTS H: TritonCTS not run (tree fully plan-built)"; return }
      set a {}
      for {set i 0} {$i < [llength $args]} {incr i} { if {[lindex $args $i] eq "-clk_nets"} { incr i; continue }; lappend a [lindex $args $i] }
      lappend a -clk_nets $::ot_ms_tapnets
      uplevel 1 [list ot_ms_cts_orig {*}$a]
    }
  }
}
