# rg2: actual buffer-stage budget, including early singleton node paths.
# HF-5b 2026-10-18: boundary clock tree of ot_hbm_accel_smh_xs (PRE_CTS extra, sourced BEFORE pre_cts_skew.tcl, so the
# io_ref boundary switch wraps it and references the boundary to THIS tree).  Same fix class as NATIVE-FIX3/shvc
# physical/ref_tile/dsdv_sh_vc/bnd_branch.tcl (closed dsdv_sh_vc-nf3bt-ce989b78c: routed boundary spread 105.7 -> 30.9 TT /
# 29.6 FF) and KH-NATIVE3 qkd_kv_grp_ctl_p; procs copied unchanged, clock port clk (not ck), depth 6.
#
# Why (lanes/HF-5.md; claude/hf5-1018 76bd52687 results/arch/hf5_1018/native/native_3_audit.json): the routed CLOSED view
# smh_xs_ref_p45m-r3-29a3f8638 (record da183de3c) fails the native audit on boundary (pin-flop) spread 106.4 TT / 101.9 FF
# (insertion.json boundary TT 268.2..374.6 over 4,513 sinks, mean 315.0; all 15,331 sinks 264..767), capture 98 pins
# (rl1 / bk1 / ohl1 landing flops: S+R median 181..193, tail to 250 = early-clocked landing flops) and launch 4 pins.
# The boundary is the 2,900-flop S-face landing band (u_rl2 / u_bkd2 / u_ohl2 behind ot_hdly, y 0..30 under the
# macro rows) + the 1,594 operand (i) stage flops at the 4 macro rd_out edges + the N/E control; the clock pin is on the
# N face (x ~125), 158 um from the landing band, and the register-mass tree reaches the two bands at different depths.
# What: after TritonCTS every core_clk boundary register moves onto one balanced tree from a stem beside the clk pin
# (geometric binary split, 6 levels = 64 BUFx24 leaves ~70 sinks each, repeaters on every wire > 80 um, every
# root -> leaf path padded to one buffer count).  The register mass + the 4 SRAM clk pins keep the CTS tree.
# No pin, outline or SDC change.
# HBM-SMHXS-HOLD 2026-10-19 (REFILL-1330): ONE TREE FOR EVERY SINK (ot_sv_all 1, the default here).
# Why: the routed hf5bt job smh_xs_ref_p45m-hf5bt-e1b14e06f (boundary-only tree) fixed the pin-flop spread (68.9 TT /
# 59.4 FF) but ended NEEDS_RTL FF -45.75 (hold ECO rc=9, 9,233 cells, least-bad -0.71).  Classified (cl/path_summary.json,
# w18_sta_ff.log): ALL failing reg->reg classes cross from the TritonCTS register-mass tree to this boundary tree on
# ZERO-LOGIC hops of the w / c delay lines (u_leaf.w3b -> o_iw 311 paths -45.75; c3bd -> o_itag/ifirst/ilast/ifp4/u_ctle
# -33.8..-16.7): launch w3b[156] CLK 255.8 (CTS leaf, 8 levels), capture o_iw[156] CLK 353.6 (svbnd, 11 levels), CRPR 0
# (no common path) -> 98 ps cross-tree skew at FF against a clk->q + wire data path.  IO class (bk1 -> u_bkd2 -30.4,
# rl1 -> u_rl2 -26.1) is the pin-flop reference band; reset landing (+15 / +18) and the 4 SRAM clk pins are clean.
# Fix: no second tree.  TritonCTS is not run; every sink of the clock port net (15,345 registers + 4 SRAM clk pins) goes
# onto this one geometric tree from the stem beside the clk pin (8 levels = 256 leaves ~60 sinks, repeaters > 80 um,
# equal buffer count per path), so every hop -- delay line, boundary, macro -- is intra-tree with a shared trunk.
# ot_sv_all 0 restores the hf5bt boundary-only tree.
if {![info exists ::ot_sv_all]}    { set ::ot_sv_all 1 }
if {![info exists ::ot_sv_depth]}  { set ::ot_sv_depth [expr {$::ot_sv_all ? 8 : 6}] }
if {![info exists ::ot_sv_gap_um]} { set ::ot_sv_gap_um 20 }
if {![info exists ::ot_sv_rep_um]} { set ::ot_sv_rep_um 80 }
if {![info exists ::ot_sv_master]} { set ::ot_sv_master BUFx24_ASAP7_75t_R }

proc ot_sv_bnd_regs {clk} {
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

# keep a buffer location off the (haloed) macros and inside the core: move it to the nearest macro edge
proc ot_sv_legal {x y} {
  set core [[ord::get_db_block] getCoreArea]
  set x [expr {int($x)}]; set y [expr {int($y)}]
  set x [expr {max([$core xMin] + 1000, min([$core xMax] - 1000, $x))}]
  set y [expr {max([$core yMin] + 1000, min([$core yMax] - 1000, $y))}]
  foreach bb $::ot_sv_macros {
    lassign $bb x0 y0 x1 y1
    if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} {
      set c [lsort -integer -index 0 [list [list [expr {$x - $x0}] $x0 $y] [list [expr {$x1 - $x}] $x1 $y] \
                                           [list [expr {$y - $y0}] $x $y0] [list [expr {$y1 - $y}] $x $y1]]]
      lassign [lindex $c 0] d x y
    }
  }
  return [list [expr {int($x)}] [expr {int($y)}]]
}

# sinks: list of {iterm x y}.  returns a tree node: {leaf x y sinks} or {node x y left right}
proc ot_sv_build {sinks depth} {
  set sx 0; set sy 0
  foreach s $sinks { incr sx [lindex $s 1]; incr sy [lindex $s 2] }
  set n [llength $sinks]
  if {$depth == 0 || $n < 2} {
    lassign [ot_sv_legal [expr {$sx / $n}] [expr {$sy / $n}]] x y
    return [list leaf $x $y $sinks]
  }
  set xs [lsort -integer [lmap s $sinks {lindex $s 1}]]; set ys [lsort -integer [lmap s $sinks {lindex $s 2}]]
  set ax [expr {[lindex $xs end] - [lindex $xs 0] >= [lindex $ys end] - [lindex $ys 0] ? 1 : 2}]
  set srt [lsort -integer -index $ax $sinks]
  # widest gap along the axis (the N / S pin bands); else the count median
  set best -1; set bi [expr {$n / 2}]
  for {set i 1} {$i < $n} {incr i} {
    set g [expr {[lindex $srt $i $ax] - [lindex $srt [expr {$i - 1}] $ax]}]
    if {$g > $best} { set best $g; set gi $i }
  }
  if {$best > $::ot_sv_gap_um * 1000} { set bi $gi }
  set l [ot_sv_build [lrange $srt 0 [expr {$bi - 1}]] [expr {$depth - 1}]]
  set r [ot_sv_build [lrange $srt $bi end] [expr {$depth - 1}]]
  lassign [ot_sv_legal [expr {([lindex $l 1] + [lindex $r 1]) / 2}] [expr {([lindex $l 2] + [lindex $r 2]) / 2}]] x y
  return [list node $x $y $l $r]
}

proc ot_sv_buf {x y} {
  set b [odb::dbInst_create [ord::get_db_block] $::ot_sv_m "clkbuf_svbnd_$::ot_sv_nb"]
  lassign [ot_sv_legal $x $y] x y
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set net [odb::dbNet_create [ord::get_db_block] "clknet_svbnd_$::ot_sv_nb"]; $net setSigType CLOCK
  [$b findITerm Y] connect $net
  incr ::ot_sv_nb
  return [list $b $net]
}

# wire from (px,py) driving net pnet to a child at (x,y): repeaters every ot_sv_rep_um; returns {net stages}
proc ot_sv_wire {pnet px py x y} {
  set d [expr {abs($x - $px) + abs($y - $py)}]
  set k [expr {int(ceil($d / ($::ot_sv_rep_um * 1000.0))) - 1}]
  for {set i 1} {$i <= $k} {incr i} {
    set f [expr {double($i) / ($k + 1)}]
    lassign [ot_sv_buf [expr {$px + ($x - $px) * $f}] [expr {$py + ($y - $py) * $f}]] b net
    [$b findITerm A] connect $pnet; set pnet $net
  }
  return [list $pnet [expr {max($k, 0)}]]
}

# count repeater stages to every leaf (dry), so paths can be padded to one buffer count
proc ot_sv_stages {t px py} {
  lassign $t kind x y
  set d [expr {abs($x - $px) + abs($y - $py)}]
  set k [expr {max(0, int(ceil($d / ($::ot_sv_rep_um * 1000.0))) - 1)}]
  if {$kind eq "leaf"} { return [expr {$k + 1}] }
  return [expr {$k + 1 + max([ot_sv_stages [lindex $t 3] $x $y], [ot_sv_stages [lindex $t 4] $x $y])}]
}

proc ot_sv_bnd_tree {port clkname} {
  set block [ord::get_db_block]
  set ::ot_sv_m [[ord::get_db] findMaster $::ot_sv_master]
  set ::ot_sv_nb 0; set ::ot_sv_ns 0
  set ::ot_sv_macros {}
  set h 4000
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] isBlock]} {
      set bb [$inst getBBox]
      lappend ::ot_sv_macros [list [expr {[$bb xMin] - $h}] [expr {[$bb yMin] - $h}] [expr {[$bb xMax] + $h}] [expr {[$bb yMax] + $h}]]
    }
  }
  set bt [$block findBTerm $port]; set pnet [$bt getNet]
  set bb [[lindex [$bt getBPins] 0] getBBox]
  lassign [ot_sv_legal [expr {([$bb xMin] + [$bb xMax]) / 2}] [expr {([$bb yMin] + [$bb yMax]) / 2}]] tx ty
  set sinks {}
  if {$::ot_sv_all} {
    # every load of the (pre-CTS, unbuffered) clock port net: register CLK pins and the SRAM clk pins
    foreach it [$pnet getITerms] {
      if {![$it isInputSignal]} continue
      set ib [[$it getInst] getBBox]
      lappend sinks [list $it [expr {([$ib xMin] + [$ib xMax]) / 2}] [expr {([$ib yMin] + [$ib yMax]) / 2}]]
    }
  }
  foreach inst [expr {$::ot_sv_all ? {} : [ot_sv_bnd_regs [get_clocks $clkname]]}] {
    set ck ""
    foreach it [$inst getITerms] { if {[$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK" && [$it isInputSignal]} { set ck $it } }
    if {$ck eq ""} continue
    set ib [$inst getBBox]
    lappend sinks [list $ck [expr {([$ib xMin] + [$ib xMax]) / 2}] [expr {([$ib yMin] + [$ib yMax]) / 2}]]
  }
  if {![llength $sinks]} { error "OT_SV_BND: no $clkname boundary registers found" }
  set t [ot_sv_build $sinks $::ot_sv_depth]
  # stem beside the ck pin on the port net
  lassign [ot_sv_buf $tx $ty] b net; [$b findITerm A] connect $pnet
  ot_sv_emit_root $t $net $tx $ty
  puts "OT_SV_BND $port (all=$::ot_sv_all): $::ot_sv_ns $clkname sinks onto a $::ot_sv_depth-level balanced tree, $::ot_sv_nb buffers\
        ($::ot_sv_master, repeat $::ot_sv_rep_um um, gap $::ot_sv_gap_um um), stem at [expr {$tx / 1000.0}] [expr {$ty / 1000.0}] um"
}

# root: the common repeater budget is the deepest path's count; every subtree is padded to it
proc ot_sv_emit_root {t net x y} {
  set ::ot_sv_path_stages {}
  ot_sv_emit $t $net $x $y [ot_sv_stages $t $x $y] 0
  set ss [lsort -integer $::ot_sv_path_stages]
  set mn [expr {[lindex $ss 0] + 1}]; set mx [expr {[lindex $ss end] + 1}]
  if {$mn != $mx} {error "OT_SV_STAGE_MISMATCH $mn $mx"}
  puts "OT_SV_EQUAL_STAGES min=$mn max=$mx leaf_groups=[llength $ss] buffers=$::ot_sv_nb (includes common stem)"
}
proc ot_sv_emit {t pnet px py budget {spent 0}} {
  lassign $t kind x y
  lassign [ot_sv_wire $pnet $px $py $x $y] pnet k
  set budget [expr {$budget - $k}]
  if {$kind eq "leaf"} {
    lappend ::ot_sv_path_stages [expr {$spent + $k + $budget}]
    for {set i 0} {$i < $budget - 1} {incr i} {
      lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet; set pnet $net
    }
    lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet
    foreach s [lindex $t 3] { set it [lindex $s 0]; $it disconnect; $it connect $net; incr ::ot_sv_ns }
    return
  }
  lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet
  foreach c [lrange $t 3 4] { ot_sv_emit $c $net $x $y [expr {$budget - 1}] [expr {$spent + $k + 1}] }
}

rename clock_tree_synthesis ::ot_sv_bnd_cts_orig
proc clock_tree_synthesis {args} {
  if {$::ot_sv_all} {
    puts "OT_SV_BND: one tree for every sink; TritonCTS not run (args $args)"
  } else {
    ::ot_sv_bnd_cts_orig {*}$args
    estimate_parasitics -placement
  }
  ot_sv_bnd_tree clk core_clk
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
}
