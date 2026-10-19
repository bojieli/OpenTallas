# KV-PROMPT4 10-18: boundary clock branch of qkd_hr_core_prompt (coordinator decision 3, gate p3 FAIL: pin-flop spread
# 114.9 ps TT > 80, 17,538 sinks, insertion 438.7, leaf spread 122.4).  Copy of physical/ref_tile/dsdv_sh_vc/bnd_branch.tcl
# (NATIVE-FIX3/shvc, closed dsdv_sh_vc; same class as qkd_kv_grp_ctl_p) with the clock port ck_core and depth 6 (this
# tile has ~4,100 boundary pin registers on all four faces vs dsdv_sh_vc's 2,072 on two bands: 64 leaves of ~65 sinks).
# Everything below is the dsdv_sh_vc technique unchanged except ::ot_sv_port / ::ot_sv_depth defaults.
# NATIVE-FIX3/shvc 2026-10-18: boundary clock tree of dsdv_sh_vc (PRE_CTS extra, sourced BEFORE pre_cts_skew.tcl, so the
# io_ref boundary switch wraps it and references the boundary to THIS tree).  Same fix class as KH-NATIVE3's
# qkd_kv_grp_ctl_p bnd_branch.tcl (boundary registers on their own clock branch = regional root for the boundary),
# extended for a tile whose boundary is two pin bands 200 um apart.
#
# Why (lanes/NATIVE-3.md, claude/native-3-1017 73adc87ea, results/arch/native_3_1017/native_3_audit.json): the routed
# CLOSED view dsdv_sh_vc-dsdv_sh_vc-7d488e37d fails NATIVE-3 on clock only: pin-flop (boundary) spread 105.7 ps TT /
# 98.7 FF (> 80), R 274.3, every pin inside launch/capture.  2,072 of the 3,238 ck sinks are boundary registers
# (source-registered pins) in the N band (y 180..214) and the S band (y 0..30), each 226.8 um wide; the register-mass
# H-tree hangs the NE N-band leaves on one fo-16 level-4 net (gate9 per-flop dump: NE 312..338 vs centre 243 ps), and
# 12 CTS knob / pin variants all stayed at 87..117 (lanes/S81U-SEQ.md SEQ5).
#
# What: after TritonCTS builds the tree, every core_clk boundary register (D from an input port or Q to an output port:
# the set closure_loop/ck_insertion.py calls "boundary") is moved off its leaf onto a dedicated balanced tree built
# here: a stem BUFx24 beside the ck pin on the port net (parallel to the register-mass root), then a geometric binary
# tree (split at the widest gap > OT_SV_GAP_UM along the longer axis -- the N/S bands -- else at the count median),
# OT_SV_DEPTH levels deep for every leaf, internal buffers at the merge midpoint of their two children (kept off the
# macros), BUFx24 leaves at their sinks' centroid; every parent -> child wire longer than OT_SV_REP_UM gets evenly
# spaced repeaters, and every root -> leaf path is padded to the same buffer count, so arrivals differ only by short
# wires.  The register mass + the three SRAM clk pins keep TritonCTS's tree.  No RTL, SDC, pin or outline change.
# Placement-RC probe on the gate9 CTS placement (3733d51e5 4_1_cts.odb, ~/scratch/nf3-shvc): boundary TT 240.2..338.2
# (spread 98.1) -> 279.3..301.5 (22.2, mean 287.6 vs mass 240..332), FF 93.4 -> 20.5, TT setup WNS +4.1 -> +32.5 ps.
# Sweep (depth / repeat um -> TT mean, spread): 7/55 363.7, 15.3; 6/55 343.1, 17.1; 5/55 325.1, 20.1; 6/80 305.7, 19.2;
# 5/80 287.6, 22.2 (chosen: keeps the boundary mean beside the closed R 274.3 and the mass); 5/110 281.2, 18.8.
if {![info exists ::ot_sv_depth]}  { set ::ot_sv_depth 6 }
if {![info exists ::ot_sv_port]}   { set ::ot_sv_port ck_core }
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
  if {$kind eq "leaf"} { return $k }
  return [expr {$k + max([ot_sv_stages [lindex $t 3] $x $y], [ot_sv_stages [lindex $t 4] $x $y])}]
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
  foreach inst [ot_sv_bnd_regs [get_clocks $clkname]] {
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
  puts "OT_SV_BND $port: $::ot_sv_ns $clkname boundary sinks onto a $::ot_sv_depth-level balanced tree, $::ot_sv_nb buffers\
        ($::ot_sv_master, repeat $::ot_sv_rep_um um, gap $::ot_sv_gap_um um), stem at [expr {$tx / 1000.0}] [expr {$ty / 1000.0}] um"
}

# root: the common repeater budget is the deepest path's count; every subtree is padded to it
proc ot_sv_emit_root {t net x y} {
  ot_sv_emit $t $net $x $y [ot_sv_stages $t $x $y]
}
proc ot_sv_emit {t pnet px py budget} {
  lassign $t kind x y
  lassign [ot_sv_wire $pnet $px $py $x $y] pnet k
  set budget [expr {$budget - $k}]
  if {$kind eq "leaf"} {
    for {set i 0} {$i < $budget} {incr i} {
      lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet; set pnet $net
    }
    lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet
    foreach s [lindex $t 3] { set it [lindex $s 0]; $it disconnect; $it connect $net; incr ::ot_sv_ns }
    return
  }
  lassign [ot_sv_buf $x $y] b net; [$b findITerm A] connect $pnet
  foreach c [lrange $t 3 4] { ot_sv_emit $c $net $x $y $budget }
}

rename clock_tree_synthesis ::ot_sv_bnd_cts_orig
proc clock_tree_synthesis {args} {
  ::ot_sv_bnd_cts_orig {*}$args
  estimate_parasitics -placement
  ot_sv_bnd_tree $::ot_sv_port core_clk
}
