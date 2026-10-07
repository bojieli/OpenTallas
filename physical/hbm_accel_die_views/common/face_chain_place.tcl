# POST_GLOBAL_PLACE hook (CLAUDE HBM-ABSTRACTS spine, route_view.sh FCP=<face_stages>): space every face chain of a
# thin registered die wrapper (tools/hbm_die_wrap.py, face_stages N) evenly between its core endpoint and its pin.
# Why: global placement clumps a register chain at its fixed end.  cp10_pd55 (cmdproc, N 5): the first output hop
# (core -> s0) carried -1,233 ps because s0..q all sat at the pin; qm2_pd55 (quant): s0 -> s1 hops -181 ps.
# The wire_stage_fence.tcl regions (svcidx) need both chain ends at terminals; a spine chain has one end in the core,
# which is placed only now, so this hook moves the chain cells directly (legalised by detailed placement next).
#   output pin P: walk back from P through flops (and the single-input cells between them, ASAP7 flops are QN-only)
#     until N flops are found; A = the core cell driving stage 0.  Stage k (0..N-1) goes to A + (k+1)/N (B - A),
#     B = centroid of every output pin reached from that flop (a shared group copy of hbm_die_wrap share_tree serves
#     several pins: it sits toward their centroid).  The last stage sits at the pin.
#   input pin P: walk forward from P through single-load flops; stage k goes to P + k/N (B - P), B = centroid of the
#     loads of the last stage (the core consumers).  When a single-load walk runs on into an output pin (a wrapper
#     pass-through, input chain + output chain), all its flops are spread evenly from P to that pin instead.
# Inputs are handled first so that an output chain fed by an input chain starts from the moved input stage.
# ORFS sources step hooks inside a proc: link every name the procs below use to a global first
global fc_n fc_ps fc_psi fc_dbu fc_x0 fc_y0 fc_x1 fc_y1 fc_dist
set fc_n [expr {[info exists ::env(OT_FC_STAGES)] ? $::env(OT_FC_STAGES) : 5}]
# per-port depth (hbm_die_wrap port_stages): OT_FC_FILE = <master>_face_stages.tcl (array fc_ps), else OT_FC_STAGES
array set fc_ps {}; array set fc_psi {}
if {[info exists ::env(OT_FC_FILE)] && $::env(OT_FC_FILE) ne ""} { source $::env(OT_FC_FILE) }
proc fc_np {bt} {
  global fc_ps fc_psi fc_n
  set port [regsub {\[.*} [$bt getName] {}]
  if {[$bt getIoType] eq "INPUT" && [info exists fc_psi($port)]} { return $fc_psi($port) }
  return [expr {[info exists fc_ps($port)] ? $fc_ps($port) : $fc_n}]
}
set fc_blk [ord::get_db_block]
set fc_dbu [$fc_blk getDbUnitsPerMicron]
set fc_core [$fc_blk getCoreArea]
set fc_x0 [$fc_core xMin]; set fc_y0 [$fc_core yMin]; set fc_x1 [$fc_core xMax]; set fc_y1 [$fc_core yMax]

proc fc_seq {inst} { return [[$inst getMaster] isSequential] }
proc fc_sig_inputs {inst} {
  set l {}
  foreach it [$inst getITerms] {
    if {[$it isOutputSignal]} continue
    if {![$it isInputSignal]} continue
    set n [$it getNet]; if {$n eq "NULL"} continue
    if {[$n getSigType] in {POWER GROUND CLOCK}} continue
    # the clock pin of a flop is on a CLOCK-typed net only after CTS: skip by master terminal type
    set mt [$it getMTerm]
    if {[$mt getSigType] eq "CLOCK" || [regexp {^(CLK|CK|clk|ck)$} [$mt getName]]} continue
    lappend l $it
  }
  return $l
}
proc fc_out_net {inst} {
  foreach it [$inst getITerms] { if {[$it isOutputSignal]} { return [$it getNet] } }
  return "NULL"
}
proc fc_driver {net} {
  if {$net eq "NULL"} { return "NULL" }
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return [$it getInst] } }
  return "NULL"
}
proc fc_loads {net} {
  set l {}
  if {$net eq "NULL"} { return $l }
  foreach it [$net getITerms] { if {![$it isOutputSignal]} { lappend l [$it getInst] } }
  return $l
}
proc fc_center {inst} {
  set b [$inst getBBox]
  return [list [expr {([$b xMin]+[$b xMax])/2.0}] [expr {([$b yMin]+[$b yMax])/2.0}]]
}
proc fc_pin {bt} {
  set b [$bt getBBox]
  return [list [expr {([$b xMin]+[$b xMax])/2.0}] [expr {([$b yMin]+[$b yMax])/2.0}]]
}
proc fc_cent {pts} {
  set sx 0.0; set sy 0.0
  foreach p $pts { set sx [expr {$sx+[lindex $p 0]}]; set sy [expr {$sy+[lindex $p 1]}] }
  return [list [expr {$sx/[llength $pts]}] [expr {$sy/[llength $pts]}]]
}
proc fc_lerp {a b f} {
  return [list [expr {[lindex $a 0]+$f*([lindex $b 0]-[lindex $a 0])}] [expr {[lindex $a 1]+$f*([lindex $b 1]-[lindex $a 1])}]]
}
array set fc_dist {}
proc fc_rec {bt a b} {
  global fc_dist fc_dbu
  set port [regsub {\[.*} [$bt getName] {}]
  lappend fc_dist($port) [expr {(abs([lindex $a 0]-[lindex $b 0])+abs([lindex $a 1]-[lindex $b 1]))/$fc_dbu}]
}
proc fc_move {inst p} {
  global fc_x0 fc_y0 fc_x1 fc_y1
  if {[info exists ::env(OT_FC_REPORT)]} return
  set m [$inst getMaster]; set w [$m getWidth]; set h [$m getHeight]
  set x [expr {round(max($fc_x0, min($fc_x1-$w, [lindex $p 0]-$w/2.0)))}]
  set y [expr {round(max($fc_y0, min($fc_y1-$h, [lindex $p 1]-$h/2.0)))}]
  $inst setLocation $x $y
  $inst setPlacementStatus PLACED
}

# Timing-driven global placement keeps the buffers of its virtual repair (keep_resize_below_overflow), placed along
# the pre-move routes: qm5_pd55 y[172] -> s0 ran 499 -> 1277 -> 762 um through five such buffers (-415 ps on a
# 318 um hop).  Remove them first (the walk then sees bare chains); 3_4 repair_design re-buffers the moved nets.
if {[info exists ::env(OT_FC_KEEPBUF)] && $::env(OT_FC_KEEPBUF)} {
  puts "OT_FC: buffers kept"
} elseif {[catch {remove_buffers} fc_err]} { puts "OT_FC: remove_buffers failed: $fc_err" } else { puts "OT_FC: buffers removed before the chain walk" }
array set fc_done {}
set n_in 0; set n_thru 0; set n_out 0; set n_moved 0
# ---- inputs (and pass-throughs)
foreach bt [$fc_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] in {POWER GROUND CLOCK}} continue
  set P [fc_pin $bt]
  set fc_n0 $fc_n; set fc_n [fc_np $bt]
  set chain {}; set cur $net; set thru ""
  while {1} {
    set ld [fc_loads $cur]
    foreach ob [$cur getBTerms] { if {[$ob getIoType] eq "OUTPUT"} { set thru $ob } }
    if {$thru ne ""} break
    if {[llength $ld] != 1} break
    set i [lindex $ld 0]
    if {[info exists fc_done([$i getName])]} break
    if {![fc_seq $i] && [llength [fc_sig_inputs $i]] != 1} break
    lappend chain [list $i [fc_seq $i]]
    set cur [fc_out_net $i]
    if {$cur eq "NULL"} break
    set nf 0; foreach c $chain { incr nf [lindex $c 1] }
    if {$thru eq "" && $nf >= 10} break
  }
  set fc_n $fc_n0
  set flops {}; foreach c $chain { if {[lindex $c 1]} { lappend flops [lindex $c 0] } }
  if {![llength $flops]} continue
  if {$thru ne ""} {
    # pass-through: every flop of the walk spread evenly from P to the output pin
    set Q [fc_pin $thru]; set m [llength $flops]; set j 0; set grp {}
    foreach c $chain {
      lassign $c i sq
      lappend grp $i
      if {$sq} {
        set p [fc_lerp $P $Q [expr {$m > 1 ? double($j)/($m-1) : 1.0}]]
        foreach g $grp { fc_move $g $p; set fc_done([$g getName]) 1; incr n_moved }
        set grp {}; incr j
      }
    }
    # cells after the last flop (its QN inverter: ASAP7 flops are QN-only) drive the output pin: they sit at the pin
    # (cpss3_pd55: left at their global-placement spot, xl's last inverter sat 450 um from its pin: xl -653 ps)
    foreach g $grp { fc_move $g $Q; set fc_done([$g getName]) 1; incr n_moved }
    set fc_done(pin:[$thru getName]) 1
    incr n_thru
    continue
  }
  # input chain: the first N flops; consumers of the last one are the core end
  set k 0; set grp {}; set last ""; set moves {}
  foreach c $chain {
    lassign $c i sq
    if {$k >= [fc_np $bt]} break
    lappend grp $i
    if {$sq} { lappend moves [list $k $grp]; set grp {}; set last $i; incr k }
  }
  if {$last eq ""} continue
  set ld [fc_loads [fc_out_net $last]]
  if {![llength $ld]} continue
  set pts {}; foreach i $ld { lappend pts [fc_center $i] }
  set B [fc_cent $pts]
  fc_rec $bt $P $B
  set nn [fc_np $bt]
  foreach mv $moves {
    lassign $mv kk grp
    set p [fc_lerp $P $B [expr {double($kk)/$nn}]]
    foreach g $grp { fc_move $g $p; set fc_done([$g getName]) 1; incr n_moved }
  }
  incr n_in
}
# ---- outputs: walk back N flops from every pin, gather pins per flop (shared group copies serve several pins)
array set fc_nn {}; array set fc_stage {}; array set fc_pins {}; array set fc_a {}; array set fc_inst {}; array set fc_hang {}
foreach bt [$fc_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  if {[info exists fc_done(pin:[$bt getName])]} continue
  set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] in {POWER GROUND CLOCK}} continue
  set P [fc_pin $bt]
  set nn [fc_np $bt]
  set k [expr {$nn - 1}]; set cur $net; set pend {}; set walked {}
  while {$k >= 0} {
    set d [fc_driver $cur]
    if {$d eq "NULL"} break
    set ins [fc_sig_inputs $d]
    if {[fc_seq $d]} {
      lappend walked [list $d $k $pend]; set pend {}
      incr k -1
    } elseif {[llength $ins] == 1} {
      # a single-input cell between two flops drives the wire: placed with the flop upstream of it
      lappend pend $d
    } else { break }
    if {![llength $ins]} break
    set cur [[lindex $ins 0] getNet]
  }
  if {$k >= 0} continue
  # core endpoint: the driver of stage 0's D net (past single-input cells)
  set A ""
  set d [fc_driver $cur]
  while {$d ne "NULL"} {
    set ins [fc_sig_inputs $d]
    if {[fc_seq $d] || [llength $ins] != 1} { set A [fc_center $d]; break }
    set d [fc_driver [[lindex $ins 0] getNet]]
  }
  # a core endpoint FLOP (e.g. quant u_aq.y) sits where global placement pulled it toward its far loads, away from
  # its own logic (qm5_pd55: y[81] 5 buffers / -83 ps from its D cone): pull it to its D-input drivers first (once)
  if {$A ne "" && [fc_seq $d] && ![info exists fc_done([$d getName])]} {
    set pts {}
    foreach it [fc_sig_inputs $d] { set dd [fc_driver [$it getNet]]; if {$dd ne "NULL" && $dd ne $d} { lappend pts [fc_center $dd] } }
    if {[llength $pts]} { set A [fc_cent $pts]; fc_move $d $A; incr n_moved }
    set fc_done([$d getName]) 1
  }
  if {$A eq ""} continue
  fc_rec $bt $A $P
  # the cells collected after a flop (pend) were walked before reaching the next flop upstream: they belong to it
  for {set q 0} {$q < [llength $walked]} {incr q} {
    lassign [lindex $walked $q] f kk pd
    set nm [$f getName]
    set fc_stage($nm) $kk; set fc_inst($nm) $f; lappend fc_pins($nm) $P; set fc_nn($nm) $nn
    if {![info exists fc_a($nm)]} { set fc_a($nm) $A }
    # pd = single-input cells between this flop and the flop downstream of it
    foreach c $pd { set fc_hang([$c getName]) [list $c $nm] }
  }
  incr n_out
}
foreach nm [array names fc_stage] {
  set B [fc_cent $fc_pins($nm)]
  set p [fc_lerp $fc_a($nm) $B [expr {double($fc_stage($nm)+1)/$fc_nn($nm)}]]
  fc_move $fc_inst($nm) $p; incr n_moved
  set fc_pos($nm) $p
}
foreach c [array names fc_hang] {
  lassign $fc_hang($c) i nm
  if {[info exists fc_pos($nm)]} { fc_move $i $fc_pos($nm); incr n_moved }
}
foreach port [lsort [array names fc_dist]] {
  set l [lsort -real $fc_dist($port)]; set n [llength $l]; set sm 0.0; foreach v $l { set sm [expr {$sm+$v}] }
  puts [format "OT_FC_DIST %s n %d mean %.0f p90 %.0f max %.0f um" $port $n [expr {$sm/$n}] [lindex $l [expr {int(0.9*($n-1))}]] [lindex $l end]]
}
puts "OT_FC: face chains N=$fc_n: $n_in input, $n_out output, $n_thru pass-through; $n_moved cells moved ([array size fc_stage] output-chain flops)"
