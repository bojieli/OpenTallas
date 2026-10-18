# HBM-SFUHW2 2026-10-18: dedicated balanced SRAM clock branch of ot_hbm_su_static_sfustore_hw (PRE_CTS extra; same
# fix class as physical/ref_tile/dsdv_sh_vc/bnd_branch.tcl, here applied to the 16 SRAM clk pins instead of the
# boundary registers).
#
# Why (lanes/HBM-SFUHW.md): route r2 hbm_su_sfustore_hw_1018-r2-3b1a8409b NEEDS_RTL TT -28.63 / FF -66.08.  Post-route
# TT the 16 SRAM clk pins land at 288..567 ps (column 0 = banks 0..3: 486..567; column 2: 289..311) against the
# registers' 331..419 (pin flops 331..393, rd_cap 330..419).  TritonCTS builds the macro tree as its own tree, puts 4
# delay buffers on its root (delaybuf_0..3_core_clk, ~100 ps, CTS-0036; -delay_buffer_derate 0 does not stop it) and
# then hangs a whole 4-macro column on one leaf net (clkbuf_leaf_2_clk: 214 ps).  Setup fails on the late launch
# (u_m/rd_out -> rd_cap, -28.6 TT) and hold on the late capture (wa_pin/a_pin/wd_pin -> u_m inputs, -66 FF).
#
# What: after TritonCTS, every SRAM clk pin is moved off the CTS macro tree onto a tree built here: a stem BUFx24 beside
# the clk port, OT_MB_PAD padding stages at the stem (the compensation against the register mass), then a geometric
# binary tree split at the count median along the longer axis (columns first, then the two macro pairs of each column),
# OT_MB_DEPTH levels deep, BUFx24 leaves beside each pair of clk pins, repeaters on every wire > OT_MB_REP_UM, and every
# root -> leaf path padded to one buffer count.  The CTS macro tree buffers left without loads are deleted.  The register
# tree is untouched.  No RTL, SDC, pin, outline or macro-placement change.
if {![info exists ::ot_mb_depth]}  { set ::ot_mb_depth 3 }
if {![info exists ::ot_mb_rep_um]} { set ::ot_mb_rep_um 80 }
if {![info exists ::ot_mb_pad]}    { set ::ot_mb_pad 1 }
if {![info exists ::ot_mb_trunk_gap_um]} { set ::ot_mb_trunk_gap_um 6 }
if {![info exists ::ot_mb_master]} { set ::ot_mb_master BUFx24_ASAP7_75t_R }

proc ot_mb_legal {x y} {
  set core [[ord::get_db_block] getCoreArea]
  set x [expr {int($x)}]; set y [expr {int($y)}]
  set x [expr {max([$core xMin] + 1000, min([$core xMax] - 1000, $x))}]
  set y [expr {max([$core yMin] + 1000, min([$core yMax] - 1000, $y))}]
  foreach bb $::ot_mb_macros {
    lassign $bb x0 y0 x1 y1
    if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} {
      set c [lsort -integer -index 0 [list [list [expr {$x - $x0}] $x0 $y] [list [expr {$x1 - $x}] $x1 $y] \
                                           [list [expr {$y - $y0}] $x $y0] [list [expr {$y1 - $y}] $x $y1]]]
      lassign [lindex $c 0] d x y
    }
  }
  return [list [expr {int($x)}] [expr {int($y)}]]
}

# sinks: {iterm x y}; returns {leaf x y sinks} | {node x y left right}; median split along the longer axis
proc ot_mb_build {sinks depth} {
  set sx 0; set sy 0
  foreach s $sinks { incr sx [lindex $s 1]; incr sy [lindex $s 2] }
  set n [llength $sinks]
  if {$depth == 0 || $n < 2} {
    lassign [ot_mb_legal [expr {$sx / $n}] [expr {$sy / $n}]] x y
    return [list leaf $x $y $sinks]
  }
  set xs [lsort -integer [lmap s $sinks {lindex $s 1}]]; set ys [lsort -integer [lmap s $sinks {lindex $s 2}]]
  set ax [expr {[lindex $xs end] - [lindex $xs 0] >= [lindex $ys end] - [lindex $ys 0] ? 1 : 2}]
  set srt [lsort -integer -index $ax $sinks]
  set bi [expr {$n / 2}]
  set l [ot_mb_build [lrange $srt 0 [expr {$bi - 1}]] [expr {$depth - 1}]]
  set r [ot_mb_build [lrange $srt $bi end] [expr {$depth - 1}]]
  set ny [expr {([lindex $l 2] + [lindex $r 2]) / 2}]
  # a split across macro columns sits on the trunk below the array: the SRAMs obstruct M1..M4, so (with the M5 layer
  # cap) no horizontal clock wire can cross a column; only the vertical (M3/M5) column feeds run up the channels
  if {$ax == 1} { set ny $::ot_mb_trunk_y }
  lassign [ot_mb_legal [expr {([lindex $l 1] + [lindex $r 1]) / 2}] $ny] x y
  return [list node $x $y $l $r]
}

proc ot_mb_buf {x y} {
  set b [odb::dbInst_create [ord::get_db_block] $::ot_mb_m "clkbuf_mbr_$::ot_mb_nb"]
  lassign [ot_mb_legal $x $y] x y
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set net [odb::dbNet_create [ord::get_db_block] "clknet_mbr_$::ot_mb_nb"]; $net setSigType CLOCK
  [$b findITerm Y] connect $net
  incr ::ot_mb_nb
  return [list $b $net]
}

proc ot_mb_wire {pnet px py x y} {
  if {abs($x - $px) > 2000 && abs($y - $py) > 2000} {
    lassign [ot_mb_seg $pnet $px $py $x $py] pnet k1
    lassign [ot_mb_buf $x $py] b net; [$b findITerm A] connect $pnet
    lassign [ot_mb_seg $net $x $py $x $y] pnet k2
    return [list $pnet [expr {$k1 + 1 + $k2}]]
  }
  return [ot_mb_seg $pnet $px $py $x $y]
}
proc ot_mb_nrep {px py x y} {
  set d [expr {abs($x - $px) + abs($y - $py)}]
  return [expr {max(0, int(ceil($d / ($::ot_mb_rep_um * 1000.0))) - 1)}]
}
proc ot_mb_wstages {px py x y} {
  if {abs($x - $px) > 2000 && abs($y - $py) > 2000} { return [expr {[ot_mb_nrep $px $py $x $py] + 1 + [ot_mb_nrep $x $py $x $y]}] }
  return [ot_mb_nrep $px $py $x $y]
}
proc ot_mb_seg {pnet px py x y} {
  set d [expr {abs($x - $px) + abs($y - $py)}]
  set k [expr {int(ceil($d / ($::ot_mb_rep_um * 1000.0))) - 1}]
  for {set i 1} {$i <= $k} {incr i} {
    set f [expr {double($i) / ($k + 1)}]
    lassign [ot_mb_buf [expr {$px + ($x - $px) * $f}] [expr {$py + ($y - $py) * $f}]] b net
    [$b findITerm A] connect $pnet; set pnet $net
  }
  return [list $pnet [expr {max($k, 0)}]]
}

proc ot_mb_stages {t px py} {
  lassign $t kind x y
  set k [ot_mb_wstages $px $py $x $y]
  if {$kind eq "leaf"} { return $k }
  return [expr {$k + max([ot_mb_stages [lindex $t 3] $x $y], [ot_mb_stages [lindex $t 4] $x $y])}]
}

proc ot_mb_emit {t pnet px py budget} {
  lassign $t kind x y
  lassign [ot_mb_wire $pnet $px $py $x $y] pnet k
  set budget [expr {$budget - $k}]
  if {$kind eq "leaf"} {
    for {set i 0} {$i < $budget} {incr i} {
      lassign [ot_mb_buf $x $y] b net; [$b findITerm A] connect $pnet; set pnet $net
    }
    lassign [ot_mb_buf $x $y] b net; [$b findITerm A] connect $pnet
    foreach s [lindex $t 3] { set it [lindex $s 0]; [$it getNet] setDoNotTouch 0; $it disconnect; $it connect $net; incr ::ot_mb_ns }
    return
  }
  lassign [ot_mb_buf $x $y] b net; [$b findITerm A] connect $pnet
  foreach c [lrange $t 3 4] { ot_mb_emit $c $net $x $y $budget }
}

# delete clock buffers (and their nets) left driving nothing; repeat up the old tree
proc ot_mb_prune {} {
  set block [ord::get_db_block]; set nd 0
  while 1 {
    set dead {}
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] isBlock] || [string match "clkbuf_mbr_*" [$inst getName]]} continue
      set out ""; set clk 0
      foreach it [$inst getITerms] {
        if {[$it isOutputSignal]} { set out [$it getNet] }
      }
      if {$out eq "" || $out eq "NULL" || [$out getSigType] ne "CLOCK"} continue
      set loads 0
      foreach it [$out getITerms] { if {[$it isInputSignal]} { incr loads } }
      if {$loads == 0 && [llength [$out getBTerms]] == 0} { lappend dead [list $inst $out] }
    }
    if {![llength $dead]} break
    foreach d $dead { lassign $d inst net; $inst setDoNotTouch 0
      foreach it [$inst getITerms] { if {[$it getNet] ne "NULL"} { [$it getNet] setDoNotTouch 0 } }
      odb::dbInst_destroy $inst; odb::dbNet_destroy $net; incr nd }
  }
  return $nd
}

proc ot_mb_tree {port} {
  set block [ord::get_db_block]
  set ::ot_mb_m [[ord::get_db] findMaster $::ot_mb_master]
  set ::ot_mb_nb 0; set ::ot_mb_ns 0
  set ::ot_mb_macros {}
  set h 4000; set sinks {}
  foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    set bb [$inst getBBox]
    lappend ::ot_mb_macros [list [expr {[$bb xMin] - $h}] [expr {[$bb yMin] - $h}] [expr {[$bb xMax] + $h}] [expr {[$bb yMax] + $h}]]
    foreach it [$inst getITerms] {
      if {[$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK" && [$it isInputSignal]} {
        lassign [$it getAvgXY] ok px py
        if {!$ok} { set px [$bb xMin]; set py [$bb yMin] }
        lappend sinks [list $it $px $py]
      }
    }
  }
  if {![llength $sinks]} { error "OT_MB: no macro clock pins found" }
  if {![info exists ::ot_mb_trunk_y]} {
    set ::ot_mb_trunk_y [expr {[tcl::mathfunc::min {*}[lmap bb $::ot_mb_macros {lindex $bb 1}]] - int($::ot_mb_trunk_gap_um * 1000)}]
  }
  set bt [$block findBTerm $port]; set pnet [$bt getNet]
  set bb [[lindex [$bt getBPins] 0] getBBox]
  lassign [ot_mb_legal [expr {([$bb xMin] + [$bb xMax]) / 2}] [expr {([$bb yMin] + [$bb yMax]) / 2}]] tx ty
  set t [ot_mb_build $sinks $::ot_mb_depth]
  set dt [$pnet isDoNotTouch]; $pnet setDoNotTouch 0
  lassign [ot_mb_buf $tx $ty] b net; [$b findITerm A] connect $pnet
  $pnet setDoNotTouch $dt
  for {set i 0} {$i < $::ot_mb_pad} {incr i} {
    lassign [ot_mb_buf $tx $ty] b n2; [$b findITerm A] connect $net; set net $n2
  }
  ot_mb_emit $t $net $tx $ty [ot_mb_stages $t $tx $ty]
  set nd [ot_mb_prune]
  puts "OT_MB $port: $::ot_mb_ns SRAM clk pins onto a $::ot_mb_depth-level balanced tree, $::ot_mb_nb buffers\
        ($::ot_mb_master, pad $::ot_mb_pad, repeat $::ot_mb_rep_um um), $nd old CTS macro-tree buffers removed,\
        stem at [expr {$tx / 1000.0}] [expr {$ty / 1000.0}] um"
}

if {![info exists ::ot_mb_probe]} {
  rename clock_tree_synthesis ::ot_mb_cts_orig
  proc clock_tree_synthesis {args} {
    ::ot_mb_cts_orig {*}$args
    ot_mb_tree clk
  }
}
# Placement-RC probe on the r2 CTS placement (4_cts.odb of hbm_su_sfustore_hw_1018-r2-3b1a8409b, TT, ~/scratch/hbm-sfuhw2):
#   CTS macro tree  300.3..385.5 (spread 85.2) at placement RC; post-route it became 288..567 (bank 2: 307 -> 567).
#   this tree, depth 3 / repeat 80: pad 0 327.3..333.2 (5.9), pad 2 371.3..377.2, pad 4 415.3..421.2; depth 4 pad 0 350.5..359.5.
#   pad 1 (default) puts the SRAM pins ~15 ps before the pin-flop mean (368.8; registers 346.8..432.0): early launch for
#   rd_out -> rd_cap setup, early capture for the pin-flop -> SRAM hold.  Every tree wire <= 80 um, so routing cannot
#   repeat the 200+ ps detour of the CTS column leaf.
# GATE 1 of this tree (cbb750936, no trunk): at placement RC 336..366 TT, but after global route 495..702: the SRAMs
#   obstruct M1..M4 and the layer cap is M5 (vertical), so every horizontal tree wire across a column detoured
#   (clknet_mbr_4 342 um routed for ~130 um HPWL; same root cause as the r1/r2 CTS macro tree lateness).
# Trunk fix (now): every split across columns sits on a trunk OT_MB_TRUNK_GAP_UM (6) below the array, wires are
#   Manhattan with a corner buffer (horizontal at the parent's y, then vertical), so only vertical column feeds enter the
#   channels.  Global-route probe on the r2 CTS placement (pad 1): SRAM clk TT 388.3..405.2 (spread 16.9) vs pin flops
#   407.6..510.2 (mean 440.7); FF 323.8..346.3 (22.5) vs 337.0..428.5 (367.6).  rd_out -> rd_cap TT setup +123.3 (r2
#   route -28.6); wa_pin -> w_addr_in FF hold +43.0 (r2 route -66.1).
