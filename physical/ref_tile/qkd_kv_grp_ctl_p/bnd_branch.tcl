# KH-NATIVE3 2026-10-17: boundary clock branch of qkd_kv_grp_ctl_p (PRE_CTS extra, sourced BEFORE pre_cts_skew.tcl, so
# the io_ref boundary switch wraps it and references the boundary to THIS branch).
#
# Why (lanes/NATIVE-2.md, claude/native-2-1017 3fd032e8e, results/arch/native_2_1017/native_2_audit.json): the routed
# view qkd_kv_grp_ctl_p-p1-a76a05b96 failed the native capture budget on 449 of 476 core-domain inputs (190.5-220.2 ps):
# one ck root drives 6,691 sinks (the five boot-CDC FIFOs' storage) through a 4-buffer H-tree, TT boundary insertion
# R = 160 ps, and the input hold pad the die-referenced boundary needs grows with R (measured cfg_data[5]: FIRM inhold
# 97 ps + 88 ps repair hold cells ahead of the pin flop), so capture = S + R lands at R + ~45 ps.
#
# What: after TritonCTS builds the register-mass tree, every core_clk BOUNDARY register (D fed from an input port, or Q
# driving an output port: the same set closure_loop/ck_insertion.py calls "boundary") is moved off its H-tree leaf onto
# a short dedicated branch: one BUFx24 trunk beside the ck pin, driven by the ck port net in parallel to the H-tree
# root buffer, feeding local BUFx24 leaves (square bins of OT_KH_BIN_UM, at most OT_KH_LEAF_MAX sinks per leaf, leaf at
# the sinks' centroid).  Two buffers port -> pin flop.  The register mass keeps its balanced tree; the pin-flop ->
# mass skew (~+55 ps, useful for setup) is closed by the normal CTS-stage hold repair inside the tile.  No RTL, SDC,
# pin or outline change.  Measured on the p1 placement (placement RC, TT): boundary R 149.2 -> 85.0 ps (spread 42.8),
# mass 144.4 -> 140.0 ps.
if {![info exists ::ot_kh_bin_um]}     { set ::ot_kh_bin_um 40 }
if {![info exists ::ot_kh_leaf_max]}   { set ::ot_kh_leaf_max 60 }
if {![info exists ::ot_kh_leaf_master]} { set ::ot_kh_leaf_master BUFx24_ASAP7_75t_R }

proc ot_kh_bnd_regs {clk} {
  set regs {}
  foreach p [all_registers -clock $clk -clock_pins] { dict set regs [get_full_name [$p instance]] 1 }
  set bnd {}
  foreach pe [find_timing_paths -path_delay max -from [all_inputs -no_clocks] -to [all_registers -data_pins] \
                -group_path_count 200000 -endpoint_path_count 1] {
    set i [[get_property $pe endpoint] instance]
    if {[dict exists $regs [get_full_name $i]]} { dict set bnd [get_full_name $i] [sta::sta_to_db_inst $i] }
  }
  foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] \
                -group_path_count 200000 -endpoint_path_count 100000] {
    set i [[get_property $pe startpoint] instance]
    if {[dict exists $regs [get_full_name $i]]} { dict set bnd [get_full_name $i] [sta::sta_to_db_inst $i] }
  }
  return [dict values $bnd]
}

proc ot_kh_bnd_branch {port clkname} {
  set block [ord::get_db_block]
  set db [ord::get_db]
  set bin [expr {int($::ot_kh_bin_um * [$block getDefUnits])}]
  set trunk_m [$db findMaster BUFx24_ASAP7_75t_R]
  set leaf_m [$db findMaster $::ot_kh_leaf_master]
  set bt [$block findBTerm $port]
  set pnet [$bt getNet]
  set bb [[lindex [$bt getBPins] 0] getBBox]
  set core [$block getCoreArea]
  set tx [expr {max([$core xMin] + 2000, min([$core xMax] - 2000, ([$bb xMin] + [$bb xMax]) / 2))}]
  set ty [expr {max([$core yMin] + 2000, min([$core yMax] - 2000, ([$bb yMin] + [$bb yMax]) / 2))}]
  set groups {}
  foreach inst [ot_kh_bnd_regs [get_clocks $clkname]] {
    set ck ""
    foreach it [$inst getITerms] { if {[$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK" && [$it isInputSignal]} { set ck $it } }
    if {$ck eq ""} continue
    lassign [$inst getLocation] x y
    dict lappend groups "[expr {$x / $bin}]_[expr {$y / $bin}]" [list $ck $x $y]
  }
  if {![dict size $groups]} { error "OT_KH_BRANCH: no $clkname boundary registers found" }
  set tb [odb::dbInst_create $block $trunk_m "clkbuf_bndtrunk_${port}"]
  $tb setLocation $tx $ty; $tb setPlacementStatus PLACED
  set tnet [odb::dbNet_create $block "clknet_bndtrunk_${port}"]; $tnet setSigType CLOCK
  [$tb findITerm A] connect $pnet; [$tb findITerm Y] connect $tnet
  set nb 0; set ns 0
  foreach key [lsort [dict keys $groups]] {
    set mem [dict get $groups $key]
    set k [expr {int(ceil([llength $mem] / double($::ot_kh_leaf_max)))}]
    for {set g 0} {$g < $k} {incr g} {
      set part [lrange $mem [expr {$g * [llength $mem] / $k}] [expr {($g + 1) * [llength $mem] / $k - 1}]]
      set sx 0; set sy 0
      foreach m $part { incr sx [lindex $m 1]; incr sy [lindex $m 2] }
      set b [odb::dbInst_create $block $leaf_m "clkbuf_bnd_${nb}_${port}"]
      $b setLocation [expr {$sx / [llength $part]}] [expr {$sy / [llength $part]}]; $b setPlacementStatus PLACED
      set net [odb::dbNet_create $block "clknet_bnd_${nb}_${port}"]; $net setSigType CLOCK
      [$b findITerm A] connect $tnet; [$b findITerm Y] connect $net
      foreach m $part { set it [lindex $m 0]; $it disconnect; $it connect $net; incr ns }
      incr nb
    }
  }
  puts "OT_KH_BRANCH $port: $ns $clkname boundary sinks onto $nb leaf buffers ($::ot_kh_leaf_master, bins $::ot_kh_bin_um um,\
        max $::ot_kh_leaf_max) under trunk clkbuf_bndtrunk_${port} at [expr {$tx / 1000.0}] [expr {$ty / 1000.0}] um"
}

rename clock_tree_synthesis ::ot_kh_bnd_cts_orig
proc clock_tree_synthesis {args} {
  ::ot_kh_bnd_cts_orig {*}$args
  estimate_parasitics -placement
  ot_kh_bnd_branch ck core_clk
}
