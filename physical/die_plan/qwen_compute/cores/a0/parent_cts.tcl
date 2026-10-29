# QC A0 PARENT kit CTS hook (QC-A0-KITS-10; die-local, opt-in recipe key "parent_trunk" of gen_core_kit_qc.py).
# Sourced from the kit PRE_CTS hook after the generated header (pt_* variables).  Wraps clock_tree_synthesis:
#   1. sink dump: register clock pins on the tile clock PORT net (UNGATED: input-face regs, enable state, reset landing)
#      and on the ICG GCLK net (GATED), hard child clock pins; any other load on those nets fails closed;
#   2. parent_cts.py cluster -> leaf clusters (ungated and gated never mixed), one CKINVDCx16 root each;
#   3. TritonCTS on the cluster nets ONLY (the caller's CTS_ARGS, -clk_nets replaced);
#   4. measured cluster insertion (placement RC, propagated): TT = arrival max, FF = arrival min;
#   5. tools/die_plan/parent_trunk_dme.py plan --ungated-split (ICG = tree node at the gated root, root merge balances
#      face vs gated by wire length) + parent_trunk_insert.tcl with ICG_INST (the RTL u_icg, ENA/SE kept);
#   6. dont_touch on the planned trunk cells and nets; fail-closed connectivity check; record pt_record.json.
# Acceptance stays the routed OCV-inclusive spread (parent_trunk_dme.py ocv on routed arrivals, <= 60 ps).
proc pt_fail {m} { error "OT_PARENT_CTS $m" }
proc pt_dir {} { expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [pwd]} }

proc pt_icg {blk} {
  set gi [$blk findInst $::pt_icg_inst]
  if {$gi eq "NULL"} {
    set hits {}
    foreach i [$blk getInsts] {
      if {[[$i getMaster] getName] eq $::pt_icg_cell && [regexp "(^|\[./\])[string map {. \.} $::pt_icg_inst]\$" [$i getName]]} {
        lappend hits $i
      }
    }
    if {[llength $hits] != 1} { pt_fail "ICG_INST $::pt_icg_inst: [llength $hits] $::pt_icg_cell matches (need exactly 1)" }
    set gi [lindex $hits 0]
  }
  if {[[$gi getMaster] getName] ne $::pt_icg_cell} { pt_fail "ICG_INST [$gi getName] is [[$gi getMaster] getName], not $::pt_icg_cell" }
  return $gi
}

proc pt_run {cts_args} {
  set blk [ord::get_db_block]; set db [ord::get_db]; set u [$blk getDefUnits]; set dir [pt_dir]
  set bt [$blk findBTerm $::pt_clk_port]
  if {$bt eq "NULL" || [$bt getNet] eq "NULL"} { pt_fail "clock port $::pt_clk_port not found / unconnected" }
  set ck [$bt getNet]
  set gi [pt_icg $blk]
  if {[[$gi findITerm CLK] getNet] ne $ck} { pt_fail "ICG [$gi getName] CLK is not on the clock port net [$ck getName]" }
  set gclk [[$gi findITerm GCLK] getNet]
  if {$gclk eq "NULL"} { pt_fail "ICG [$gi getName] GCLK unconnected" }
  # 1. sink dump
  set regck [dict create]
  foreach p [all_registers -clock_pins] {
    set it [sta::sta_to_db_pin $p]
    if {$it ne "NULL" && $it ne ""} { dict set regck "[[$it getInst] getName]/[[$it getMTerm] getName]" 1 }
  }
  set fh [open $dir/pt_sinks.txt w]
  set die [$blk getDieArea]
  puts $fh "DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax] $u"
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; puts $fh "MACRO [$i getName] [[$i getMaster] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]" }
  }
  set ::pt_regit [dict create]; set bad {}; set nreg 0; set nkid 0
  foreach {net ung} [list $ck 1 $gclk 0] {
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set inst [$it getInst]; set m [[$inst getMaster] getName]; set pn [[$it getMTerm] getName]
      if {$inst eq $gi} continue
      set b [$it getBBox]; set x [expr {([$b xMin]+[$b xMax])/2}]; set y [expr {([$b yMin]+[$b yMax])/2}]
      if {[lsearch -exact $::pt_children $m] >= 0 && $pn eq $::pt_child_pin} {
        if {$ung} { lappend bad "[$inst getName]/$pn (hard child on the ungated port net)"; continue }
        puts $fh "SINK [$inst getName] $m $pn $x $y 0 1"; incr nkid
      } elseif {[dict exists $regck "[$inst getName]/$pn"]} {
        puts $fh "SINK [$inst getName] $m $pn $x $y $ung 0"; dict set ::pt_regit [$inst getName] $it; incr nreg
      } else {
        lappend bad "[$inst getName]/$pn ($m)"
      }
    }
  }
  close $fh
  if {[llength $bad]} { pt_fail "[llength $bad] clock loads that are neither registers nor hard child clock pins: [lrange $bad 0 9]" }
  puts "OT_PARENT_CTS sinks: $nreg register clock pins, $nkid hard child clock pins (port [$ck getName], gated [$gclk getName])"
  # 2. clusters
  if {[catch {exec python3 -I $::pt_py cluster $dir/pt_sinks.txt $dir/pt_cl.json $dir/pt_cl.tcl $::pt_maxd $::pt_maxn} msg]} { pt_fail "cluster: $msg" }
  puts $msg
  source $dir/pt_cl.tcl
  set inv [$db findMaster $::pt_root_cell]
  set nets {}
  foreach cdef $PT_CL {
    lassign $cdef name x y ung regs
    set n [odb::dbNet_create $blk $name]; $n setSigType CLOCK
    set i [odb::dbInst_create $blk $inv ${name}_root]
    $i setLocation [expr {int($x*$u)}] [expr {int($y*$u)}]; $i setPlacementStatus PLACED
    [$i findITerm A] connect [expr {$ung ? $ck : $gclk}]; [$i findITerm Y] connect $n
    foreach r $regs {
      if {![dict exists $::pt_regit $r]} { pt_fail "cluster $name register $r not in the sink dump" }
      set it [dict get $::pt_regit $r]; $it disconnect; $it connect $n
    }
    lappend nets $name
  }
  detailed_placement
  # 3. TritonCTS on the cluster nets only
  set a {}; set skip 0
  foreach x $cts_args { if {$skip} {set skip 0; continue}; if {$x eq "-clk_nets"} {set skip 1; continue}; lappend a $x }
  puts "OT_PARENT_CTS TritonCTS on [llength $nets] cluster nets only"
  ::ot_pt_tritoncts {*}$a -clk_nets $nets
  # 4. measured cluster insertion (placement RC, propagated clock)
  estimate_parasitics -placement
  set_propagated_clock [all_clocks]
  set cl [dict create]; foreach n $nets { dict set cl $n 1 }
  set fh [open $dir/pt_arr.txt w]
  foreach p [all_registers -clock_pins] {
    set it [sta::sta_to_db_pin $p]
    if {$it eq "NULL" || $it eq "" || [$it getNet] eq "NULL"} continue
    set nn [[$it getNet] getName]
    # a register on a TritonCTS sub-net of a cluster: walk up the clock buffers to the cluster net
    set w [$it getNet]; set hop 0
    while {![dict exists $cl [$w getName]] && $hop < 32} {
      set d [$w getFirstOutput]
      if {$d eq "NULL" || $d eq ""} break
      set ai [[$d getInst] findITerm A]
      if {$ai eq "NULL" || [$ai getNet] eq "NULL"} break
      set w [$ai getNet]; incr hop
    }
    if {![dict exists $cl [$w getName]]} continue
    puts $fh "S [get_full_name $p] [$w getName] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise]"
  }
  foreach n $nets {
    set p [get_pins ${n}_root/A]
    # the root is an INVERTER: the register rise edge follows the root A FALL edge (DIE-QC-18 clins.py reference)
    puts $fh "T ${n}_root/A [get_property $p arrival_max_fall] [get_property $p arrival_min_fall]"
  }
  close $fh
  if {[catch {exec python3 -I $::pt_py clins $dir/pt_arr.txt $dir/pt_cl.json $dir/pt_clins.json} msg]} { pt_fail "clins: $msg" }
  puts $msg
  # 5. plan + insert
  if {[llength $::pt_entry] == 2} { lassign $::pt_entry ex ey } else {
    set b [$bt getBBox]; set ex [expr {([$b xMin]+[$b xMax])/2.0/$u}]; set ey [expr {([$b yMin]+[$b yMax])/2.0/$u}]
  }
  set entry [format "%.3f,%.3f" $ex $ey]
  if {[catch {exec python3 -I $::pt_dme plan $dir/pt_cl.json $dir/pt_clins.json $dir/pt_trunk.json --entry $entry \
                --ungated-split --topology $::pt_topology --prefix $::pt_prefix \
                --icg-cell $::pt_icg_cell --icg-note "RTL [$gi getName] reused (ICG_INST), RTL ENA/SE kept" {*}$::pt_plan_opts > $dir/pt_plan.log} msg]} {
    pt_fail "plan: $msg"
  }
  if {[catch {exec python3 -I $::pt_dme tcl $dir/pt_trunk.json $dir/pt_trunk.tcl} msg]} { pt_fail "tcl: $msg" }
  set ::env(CLK_NET) [$ck getName]; set ::env(TTCL) $dir/pt_trunk.tcl; set ::env(ICG_INST) [$gi getName]
  set ::env(ICG_CELL) $::pt_icg_cell; set ::env(OT_PT_NO_IO) 1; set ::env(PREFIX) $::pt_prefix
  set ::env(CHILD_PIN) $::pt_child_pin; set ::env(ROOT_SUFFIX) _root; set ::env(ROOT_PIN) A
  source $::pt_insert
  # TritonCTS -repair_clock_nets also buffers the nets ABOVE the cluster roots (ck / GCLK -> roots: wire*/max_length*/
  # load_slew* repeaters); the planned trunk now drives every root, so those repeaters are left without loads: remove
  # them (iteratively, chains from the load end).  A repeater that still has a load stays and fails the check below.
  set gone 0
  while 1 {
    set cone {}; set todo [list $ck $gclk]; set seen [dict create]
    while {[llength $todo]} {
      set n [lindex $todo 0]; set todo [lrange $todo 1 end]
      if {[dict exists $seen [$n getName]]} continue
      dict set seen [$n getName] 1
      foreach it [$n getITerms] {
        set i [$it getInst]
        if {![$it isInputSignal] || $i eq $gi || [string match "${::pt_prefix}_*" [$i getName]]} continue
        set o [$i getFirstOutput]
        if {$o eq "NULL" || $o eq "" || [llength [$i getITerms]] > 4} continue
        lappend cone $i
        if {[$o getNet] ne "NULL"} { lappend todo [$o getNet] }
      }
    }
    set del 0
    foreach i $cone {
      set on [[$i getFirstOutput] getNet]
      set nl 0
      if {$on ne "NULL"} { foreach it [$on getITerms] { if {[$it isInputSignal]} {incr nl} }; incr nl [llength [$on getBTerms]] }
      if {$nl == 0} { odb::dbInst_destroy $i; if {$on ne "NULL"} { odb::dbNet_destroy $on }; incr del }
    }
    incr gone $del
    if {!$del} break
  }
  puts "OT_PARENT_CTS removed $gone load-less TritonCTS root-net repeaters above the cluster roots"
  # 6. dont_touch the planned trunk + fail-closed connectivity
  set ntr 0; set trn [dict create]
  foreach i [$blk getInsts] {
    if {[string match "${::pt_prefix}_*" [$i getName]] || $i eq $gi} {
      $i setDoNotTouch 1; incr ntr
      foreach it [$i getITerms] { if {[$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK"} { dict set trn [[$it getNet] getName] [$it getNet] } }
    }
  }
  dict for {k n} $trn { $n setDoNotTouch 1 }
  set bad {}
  foreach it [$ck getITerms] {
    if {[$it isInputSignal] && ![[$it getInst] isDoNotTouch]} { lappend bad "[[$it getInst] getName] on [$ck getName]" }
  }
  foreach it [$gclk getITerms] {
    if {[$it isInputSignal] && ![[$it getInst] isDoNotTouch]} { lappend bad "[[$it getInst] getName] on [$gclk getName]" }
  }
  foreach n $nets {
    set r [$blk findInst ${n}_root]
    set an [[$r findITerm A] getNet]
    if {$an eq "NULL" || ![$an isDoNotTouch]} { lappend bad "${n}_root/A not on a planned trunk net" }
  }
  if {[llength $bad]} { pt_fail "after insert [llength $bad] clock loads off the planned trunk: [lrange $bad 0 9]" }
  set fh [open $dir/pt_record.json w]
  puts $fh "{\"schema\":\"opentallas.qc.parent_cts.v1\",\"clusters\":[llength $nets],\"registers\":$nreg,\"children\":$nkid,\"trunk_dont_touch_insts\":$ntr,\"trunk_dont_touch_nets\":[dict size $trn],\"removed_root_net_repeaters\":$gone,\"entry\":\"$entry\",\"icg\":\"[$gi getName]\",\"plan\":\"pt_trunk.json\"}"
  close $fh
  puts "OT_PARENT_CTS planned trunk inserted: $ntr dont_touch cells, [dict size $trn] nets; record $dir/pt_record.json"
}

if {![llength [info commands ::ot_pt_tritoncts]]} {
  rename ::clock_tree_synthesis ::ot_pt_tritoncts
  proc ::clock_tree_synthesis {args} { pt_run $args }
}
