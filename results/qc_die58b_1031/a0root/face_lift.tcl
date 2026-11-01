# DIE-QC-58B face-branch clock latency lift (kit-local, GENERATED into the kit by derive_icg1_kit.py --face-lift).
# Problem (NK B2 CTS probe, FF scene BC): port face flops sit on the ungated ck tree at ~495 ps, the gated body (ck_g
# behind the single tile-root ICG) at ~647 ps -> face->body zero-logic hold -143 ps (tap_q -> xl_q / ib_i), while the
# declared FF boundary frame (OT_VCLK_FF, the parent's insertion contract) is 576.5 ps: the faces are early of their
# own frame.  Fix: after CTS, before the structural hold gate / hold repair, lift every face-flop clock leaf group to
# the declared frame with a short buffer chain inserted between its leaf clock net and the face sinks (face sinks only;
# body sinks on a mixed leaf net stay on the original net).  The chain is grown one stage per round and re-measured in
# the synchronized FF scene, so the lift lands on the frame within one stage and never overshoots it by more than one
# stage delay.  The IO frame itself is unchanged (vclk stays bound to the declared / measured face mean).
# Knobs: OT_FACE_LIFT=1 on; OT_FACE_LIFT_TARGET (default OT_VCLK_FF); OT_FACE_LIFT_CELL (BUFx4_ASAP7_75t_R);
#        OT_FACE_LIFT_TOL ps (default 6); OT_FACE_LIFT_ROUNDS (default 12).
proc ot_fl_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_fl_arr {iname} {
  # iname = ODB name (brackets escaped, as in ot_face_flops.txt); STA pattern takes the same escaped form
  set p [get_pins -quiet "$iname/CLK"]
  if {[llength $p] != 1} { return "" }
  return [ot_mm_arrival_bc $p arrival_min_rise]
}
proc ot_face_lift {} {
  if {[info exists ::ot_fl_done]} { return }
  if {[catch {ot_hold_stage} st] || $st ne "cts"} { return }
  set ::ot_fl_done 1
  set target [ot_fl_env OT_FACE_LIFT_TARGET [ot_fl_env OT_VCLK_FF ""]]
  if {![string is double -strict $target]} { puts "OT_FACE_LIFT skip: no target frame"; return }
  set tol [ot_fl_env OT_FACE_LIFT_TOL 6.0]
  set rounds [ot_fl_env OT_FACE_LIFT_ROUNDS 12]
  set block [ord::get_db_block]
  set master [[ord::get_db] findMaster [ot_fl_env OT_FACE_LIFT_CELL BUFx4_ASAP7_75t_R]]
  if {$master eq "NULL"} { error "OT_FACE_LIFT: buffer master missing" }
  set ff [glob $::env(RESULTS_DIR)/ot_face_flops.txt]
  # group face flops by their CTS leaf clock net
  set grp [dict create]
  set fh [open $ff]
  while {[gets $fh l] >= 0} {
    lassign [split $l "\t"] n side x y port
    if {$port eq "-" || $port eq ""} continue
    set nm $n
    set i [$block findInst $nm]; if {$i eq "NULL"} continue
    set it [$i findITerm CLK]; if {$it eq "NULL"} continue
    set net [$it getNet]; if {$net eq "NULL"} continue
    dict lappend grp [$net getName] $nm
  }
  close $fh
  set cur [dict create]; set arr [dict create]
  dict for {nn insts} $grp { dict set cur $nn [$block findNet $nn] }
  set nbuf 0; set k 0
  for {set r 0} {$r <= $rounds} {incr r} {
    set need {}
    set lo 1e9; set hi -1e9
    dict for {nn insts} $grp {
      set a 1e9
      foreach i $insts { set v [ot_fl_arr $i]; if {[string is double -strict $v] && $v < $a} { set a $v } }
      if {$a >= 1e9} continue
      dict set arr $nn $a
      if {$a < $lo} { set lo $a }; if {$a > $hi} { set hi $a }
      if {$a < $target - $tol} { lappend need $nn }
    }
    puts [format "OT_FACE_LIFT round %d: %d leaf groups, face arrival %.1f..%.1f ps (target %.1f), %d below target-%.1f, %d buffers so far" \
      $r [dict size $grp] $lo $hi $target [llength $need] $tol $nbuf]
    if {![llength $need] || $r == $rounds} break
    foreach nn $need {
      set src [dict get $cur $nn]
      set insts [dict get $grp $nn]
      set sx 0; set sy 0; set its {}
      foreach i $insts {
        set ii [$block findInst $i]; set it [$ii findITerm CLK]
        lappend its $it
        lassign [$ii getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]
      }
      set nb [llength $its]
      set b [odb::dbInst_create $block $master "ot_face_lift_[incr k]"]
      $b setLocation [expr {int($sx / $nb)}] [expr {int($sy / $nb)}]
      $b setPlacementStatus PLACED
      set dn [odb::dbNet_create $block "ot_face_lift_net_$k"]
      $dn setSigType CLOCK
      foreach it $its { $it disconnect; $it connect $dn }
      [$b findITerm A] connect $src
      [$b findITerm Y] connect $dn
      dict set cur $nn $dn
      incr nbuf
    }
    estimate_parasitics -placement
  }
  # global connect of the new cells' supplies is done by the flow like any resizer buffer
  catch {global_connect}
  log_cmd detailed_placement
  estimate_parasitics -placement
  if {[info exists ::ot_mm_synced]} { ot_mm_unsync; ot_mm_sync }
  puts [format "OT_FACE_LIFT done: %d buffers on %d face leaf groups, face arrival %.1f..%.1f ps vs declared frame %.1f ps" \
    $nbuf [dict size $grp] $lo $hi $target]
}
if {[info exists ::env(OT_FACE_LIFT)] && $::env(OT_FACE_LIFT) eq "1"} {
  rename ot_hold_structural_gate ot_hold_structural_gate_fl
  proc ot_hold_structural_gate {} { ot_face_lift; ot_hold_structural_gate_fl }
}
