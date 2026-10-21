# SQK-CB16C 10-21 (rgxc MAIN): channel-routed, corner-matched regional clock distribution for the 16 region roots of the
# CB16 parent (successor of cb16_ckkm.tcl for qfd_c_b16_rgx*).
# Why (measured, rgxb gate ep9 qfd_c_b16_rgxb-20261021-053531, cts.log): one TritonCTS tree per region port over ~80 sinks
# whose centroid is the middle of the 457.9 x 1166.4 A0 macro -> unbuffered spans over the A0 (no rows there), native
# insertion 1.06..2.52 ns, in-port spread 452..963 ps; cb16_ckkm then padded 25,782 cells to align TT to 25.8 ps, but wire
# delay does not scale with the corner while the pads do: at FF the same tree splits by ~400 ps (OT_QC_IO pin registers
# 2001..2529 ps across rows, QDM PINFLOP range 2103..2529) -> TT setup -583 ps / FF hold -281 ps between neighbouring flops.
# Structure here (buffers only; same RTL, ports, clocks, flops, SDC, cycles):
#  (1) every region port drives a buffered TRUNK (one OT_CKR_BUF every OT_CKR_STEP_UM) along an L path in the channels from
#      its pin to the region RING = the A0 outline of that region expanded by OT_CKR_GAP_UM (inside the 129.6..319.7 um
#      channels), then two buffered CHAINS around the ring (both directions from the entry point);
#  (2) every clock sink of the port (scalar FFs AND hard-child clock pins: A0, stations, ring tiles, xstn) is grouped by
#      (ring segment of OT_CKR_SEG_UM, recorded child insertion bin of OT_CKR_INS_BIN_PS) -> one local root per group,
#      tapped from the nearest chain buffer; TritonCTS builds only these short local trees (-clk_nets = local nets);
#  (3) after CTS every group's latest arrival (+ recorded TT child insertion) is measured for all ports in one STA pass and
#      early groups get pads of the SAME master as the trunk / chains, laid out as OT_CKR_PAD_HOP_UM hops along their
#      channel, i.e. every clock path is the same stage (buffer + ~40 um wire) repeated -> TT and FF move together.
#      Target = latest group of ALL ports (the hardened landing rings read single-cycle between neighbouring regions).
# Knobs: OT_CKR_PORTS (^ck_c[0-3]r[0-3]$) OT_CKR_BUF (BUFx4_ASAP7_75t_R) OT_CKR_ROOT (BUFx8_ASAP7_75t_R) OT_CKR_STEP_UM (40)
#        OT_CKR_GAP_UM (43.2) OT_CKR_SEG_UM (160) OT_CKR_INS_BIN_PS (30) OT_CKR_PAD_HOP_UM (40) OT_CKR_ITERS (12)
#        OT_CKR_TOL_PS (15) OT_CKR_PADB_HOP_UM (160) OT_CKR_DMAX_UM (200).  Logs: CKR: / OT_CKR lines (per-port TT spread and FF-estimate spread every iteration).
proc ot_ckr_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
set ::ot_ckr_ins [dict create qfd_c_stn514 96.6 qfd_c_stn516 95.7 qfd_c_xstn_safe 141.9 qfd_c_xstnw_safe 137.8 \
  qfd_tile_nk_rp2_romleaf_rr 174.5 qfd_tile_nl_rp2_romleaf_rr 174.5 qfd_c_ring516 137.3 qfd_c_ring514 136.7]
set ::ot_ckr_ins_pin [dict create ck_node 243.1 ck 190.5 ck_tx3 202.0 ck_tx4 219.4 ck_tx5 214.1 \
  ck_lsl0 165.3 ck_lsl1 165.3 ck_lsl2 165.3 ck_lsl3 165.3 ck_lsl4 165.3 ck_lsl5 165.3 ck_lsl6 165.3 ck_lsl7 165.3 \
  ck_rp0 201.5 ck_rp1 201.5 ck_rp2 201.5 ck_rp3 201.5 ck_rp4 201.5 ck_rp5 201.5 ck_rp6 201.5 ck_rp7 201.5 ck_rp8 201.5 ck_rp9 201.5]
proc ot_ckr_child_ins {it} {
  set m [[$it getInst] getMaster]
  if {![$m isBlock]} { return 0.0 }
  set mn [$m getName]; set pn [[$it getMTerm] getName]
  if {[string match qfd_tile_n?_rp2_romleaf_rr $mn]} {
    if {[dict exists $::ot_ckr_ins_pin $pn]} { return [dict get $::ot_ckr_ins_pin $pn] }
    return 150.0
  }
  if {[dict exists $::ot_ckr_ins $mn]} { return [dict get $::ot_ckr_ins $mn] }
  return 0.0
}
# ---- geometry (um) ----
proc ot_ckr_macros {} {
  if {[info exists ::ot_ckr_mac]} { return $::ot_ckr_mac }
  set u [[ord::get_db_tech] getDbUnitsPerMicron]; set ::ot_ckr_mac {}
  foreach inst [[ord::get_db_block] getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    set b [$inst getBBox]
    lappend ::ot_ckr_mac [list [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}] [expr {[$b xMax] / double($u)}] [expr {[$b yMax] / double($u)}]]
  }
  return $::ot_ckr_mac
}
proc ot_ckr_blocked {x y} {
  foreach r [ot_ckr_macros] {
    lassign $r a b c d
    if {$x > $a - 3.0 && $x < $c + 3.0 && $y > $b - 3.0 && $y < $d + 3.0} { return 1 }
  }
  return 0
}
# nearest free point (outside every hard child, inside the core) to (x,y): rings of 2.7 um up to 120 um, then 10.8 um up to 600
proc ot_ckr_free {x y} {
  set W $::ot_ckr_W; set H $::ot_ckr_H
  set x [expr {min(max($x, 6.0), $W - 6.0)}]; set y [expr {min(max($y, 6.0), $H - 6.0)}]
  if {![ot_ckr_blocked $x $y]} { return [list $x $y] }
  for {set r 2.7} {$r <= 600.0} {set r [expr {$r < 120.0 ? $r + 2.7 : $r + 10.8}]} {
    foreach {dx dy} [list 0 $r 0 -$r $r 0 -$r 0 $r $r -$r $r $r -$r -$r -$r] {
      set nx [expr {$x + $dx}]; set ny [expr {$y + $dy}]
      if {$nx < 6.0 || $ny < 6.0 || $nx > $W - 6.0 || $ny > $H - 6.0} continue
      if {![ot_ckr_blocked $nx $ny]} { return [list $nx $ny] }
    }
  }
  incr ::ot_ckr_nblocked
  return [list $x $y]
}
# does the straight segment cross a LARGE hard child (A0: no rows to buffer in)?
proc ot_ckr_seg_blocked {x0 y0 x1 y1} {
  foreach r [ot_ckr_macros] {
    lassign $r a b c d
    if {$c - $a < 300.0 && $d - $b < 300.0} continue
    if {max($x0, $x1) > $a && min($x0, $x1) < $c && max($y0, $y1) > $b && min($y0, $y1) < $d} { return 1 }
  }
  return 0
}
proc ot_ckr_ring_pt {R s} {
  lassign $R x0 y0 x1 y1; set w [expr {$x1 - $x0}]; set h [expr {$y1 - $y0}]; set P [expr {2 * ($w + $h)}]
  set s [expr {fmod(fmod($s, $P) + $P, $P)}]
  if {$s < $w} { return [list [expr {$x0 + $s}] $y0 h] }
  if {$s < $w + $h} { return [list $x1 [expr {$y0 + $s - $w}] v] }
  if {$s < 2 * $w + $h} { return [list [expr {$x1 - ($s - $w - $h)}] $y1 h] }
  return [list $x0 [expr {$y1 - ($s - 2 * $w - $h)}] v]
}
proc ot_ckr_ring_s {R x y} {
  lassign $R x0 y0 x1 y1; set w [expr {$x1 - $x0}]; set h [expr {$y1 - $y0}]
  set cx [expr {min(max($x, $x0), $x1)}]; set cy [expr {min(max($y, $y0), $y1)}]
  if {$cx > $x0 && $cx < $x1 && $cy > $y0 && $cy < $y1} {   # inside: nearest side
    set d [list [expr {$cy - $y0}] b [expr {$x1 - $cx}] r [expr {$y1 - $cy}] t [expr {$cx - $x0}] l]
    set best [lindex [lsort -real -stride 2 -index 0 $d] 1]
    switch $best { b { set cy $y0 } r { set cx $x1 } t { set cy $y1 } l { set cx $x0 } }
  }
  if {$cy == $y0} { return [expr {$cx - $x0}] }
  if {$cx == $x1} { return [expr {$w + $cy - $y0}] }
  if {$cy == $y1} { return [expr {$w + $h + $x1 - $cx}] }
  return [expr {2 * $w + $h + $y1 - $cy}]
}
proc ot_ckr_mkbuf {name master x y} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  lassign [ot_ckr_free $x $y] fx fy
  set b [odb::dbInst_create $blk $master $name]
  $b setLocation [expr {int($fx * $u)}] [expr {int($fy * $u)}]; $b setPlacementStatus PLACED
  set net [odb::dbNet_create $blk ${name}_clk]; $net setSigType CLOCK
  [$b findITerm Y] connect $net
  return [list $b $net]
}
proc ot_ckr_build {port} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  if {[$blk findInst ot_ckr_${port}_t0] ne "NULL"} { return }
  if {![regexp {^ck_c([0-9]+)r([0-9]+)$} $port -> c r]} { error "CKR: port name $port" }
  set a0 [$blk findInst u_t_${c}_${r}]
  if {$a0 eq "NULL"} { error "CKR: no A0 u_t_${c}_${r} for $port" }
  set bb [$a0 getBBox]; set g [ot_ckr_env OT_CKR_GAP_UM 43.2]
  set R [list [expr {max(12.0, [$bb xMin] / double($u) - $g)}] [expr {max(12.0, [$bb yMin] / double($u) - $g)}] \
              [expr {min($::ot_ckr_W - 12.0, [$bb xMax] / double($u) + $g)}] [expr {min($::ot_ckr_H - 12.0, [$bb yMax] / double($u) + $g)}]]
  lassign $R x0 y0 x1 y1; set P [expr {2 * ($x1 - $x0 + $y1 - $y0)}]
  set bt [$blk findBTerm $port]; set pnet [$bt getNet]
  set pb [$bt getBBox]; set px [expr {([$pb xMin] + [$pb xMax]) / 2.0 / $u}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2.0 / $u}]
  set sE [ot_ckr_ring_s $R $px $py]; lassign [ot_ckr_ring_pt $R $sE] ex ey
  # sinks
  set sinks {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    if {[[[$it getInst] getMaster] isBlock]} {
      set b [$it getBBox]; set x [expr {([$b xMin] + [$b xMax]) / 2.0 / $u}]; set y [expr {([$b yMin] + [$b yMax]) / 2.0 / $u}]
    } else { lassign [[$it getInst] getLocation] x y; set x [expr {$x / double($u)}]; set y [expr {$y / double($u)}] }
    set off [expr {fmod([ot_ckr_ring_s $R $x $y] - $sE + 2 * $P, $P)}]
    if {$off > $P / 2.0} { set off [expr {$off - $P}] }
    lappend sinks [list $it $x $y $off [ot_ckr_child_ins $it]]
  }
  set step [ot_ckr_env OT_CKR_STEP_UM 40.0]; set seg [ot_ckr_env OT_CKR_SEG_UM 160.0]; set ib [ot_ckr_env OT_CKR_INS_BIN_PS 30.0]
  set mb [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx4_ASAP7_75t_R]]
  set mr [[ord::get_db] findMaster [ot_ckr_env OT_CKR_ROOT BUFx8_ASAP7_75t_R]]
  # trunk: L path pin -> entry (W/E face: horizontal first; N/S face: vertical first), one buffer every step
  set onx [expr {$px < 1.0 || $px > $::ot_ckr_W - 1.0}]
  set pts [list [list $px $py]]
  if {$onx} {
    # W/E face: horizontal run at the port row; if it would cross an A0, first slide along the face strip to the nearest
    # row whose horizontal run is free (channel), then across, then to the entry
    set yr $py
    if {[ot_ckr_seg_blocked $px $py $ex $py]} {
      for {set d 10.8} {$d < 1500.0} {set d [expr {$d + 10.8}]} {
        if {![ot_ckr_seg_blocked $px [expr {$py + $d}] $ex [expr {$py + $d}]]} { set yr [expr {$py + $d}]; break }
        if {![ot_ckr_seg_blocked $px [expr {$py - $d}] $ex [expr {$py - $d}]]} { set yr [expr {$py - $d}]; break }
      }
      set xs [expr {$px < 1.0 ? $px + 20.0 : $px - 20.0}]
      lappend pts [list $xs $py] [list $xs $yr]
      puts [format "CKR: %s trunk detour along the face strip %.1f -> %.1f" $port $py $yr]
    }
    lappend pts [list $ex $yr]
  } else { lappend pts [list $px $ey] }
  lappend pts [list $ex $ey]
  set tr {}
  foreach {a} [lrange $pts 0 end-1] {b} [lrange $pts 1 end] {
    lassign $a ax ay; lassign $b bx by
    set L [expr {abs($bx - $ax) + abs($by - $ay)}]; set n [expr {max(1, int(ceil($L / $step)))}]
    for {set k 1} {$k <= $n} {incr k} {
      set f [expr {$k / double($n)}]
      lappend tr [list [expr {$ax + $f * ($bx - $ax)}] [expr {$ay + $f * ($by - $ay)}]]
    }
  }
  set tr [lrange $tr 0 end-1]; lappend tr [list $ex $ey]
  set drv $pnet; set k 0
  foreach p $tr {
    lassign [ot_ckr_mkbuf ot_ckr_${port}_t$k $mb {*}$p] b net
    [$b findITerm A] connect $drv; set drv $net; incr k
  }
  set ntr $k
  # chains around the ring from the entry; chain index 0 = trunk end
  set maxp 0.0; set maxn 0.0
  foreach s $sinks { set o [lindex $s 3]; if {$o > $maxp} { set maxp $o }; if {-$o > $maxn} { set maxn [expr {-$o}] } }
  set ch(p,0) $drv; set ch(n,0) $drv
  foreach dir {p n} lim [list $maxp $maxn] sg {1 -1} {
    set n [expr {int(ceil($lim / $step))}]
    for {set k 1} {$k <= $n} {incr k} {
      lassign [ot_ckr_ring_pt $R [expr {$sE + $sg * $k * $step}]] x y
      lassign [ot_ckr_mkbuf ot_ckr_${port}_${dir}$k $mb $x $y] b net
      [$b findITerm A] connect $ch($dir,[expr {$k - 1}]); set ch($dir,$k) $net
    }
    set nch($dir) $n
  }
  # groups (segment, insertion bin), each bisected along its longer axis until its half-perimeter <= OT_CKR_DMAX_UM;
  # local root ON the ring (channel) at the group's mean ring offset, tapped from the nearest chain buffer
  set dlim [ot_ckr_env OT_CKR_DMAX_UM 200.0]
  array unset grp
  foreach s $sinks {
    lassign $s it x y off ins
    lappend grp("[expr {int(floor($off / $seg))}]_[expr {int(round($ins / $ib))}]") $s
  }
  set todo {}
  foreach key [lsort [array names grp]] { lappend todo $grp($key) }
  set ng 0; set dmax 0.0
  while {[llength $todo]} {
    set mem [lindex $todo 0]; set todo [lrange $todo 1 end]
    set xs [lsort -real [lmap s $mem {lindex $s 1}]]; set ys [lsort -real [lmap s $mem {lindex $s 2}]]
    set wx [expr {[lindex $xs end] - [lindex $xs 0]}]; set wy [expr {[lindex $ys end] - [lindex $ys 0]}]
    if {$wx + $wy > $dlim && [llength $mem] > 1} {
      set ax [expr {$wx >= $wy ? 1 : 2}]
      set srt [lsort -real -index $ax $mem]; set h [expr {[llength $srt] / 2}]
      lappend todo [lrange $srt 0 [expr {$h - 1}]] [lrange $srt $h end]
      continue
    }
    set co 0.0; foreach s $mem { set co [expr {$co + [lindex $s 3]}] }; set co [expr {$co / [llength $mem]}]
    set dir [expr {$co >= 0 ? "p" : "n"}]; set ci [expr {min($nch($dir), int(round(abs($co) / $step)))}]
    lassign [ot_ckr_ring_pt $R [expr {$sE + $co}]] rx ry side
    lassign [ot_ckr_mkbuf ot_ckr_${port}_g$ng $mr $rx $ry] b net
    [$b findITerm A] connect $ch($dir,$ci)
    foreach s $mem { set it [lindex $s 0]; $it disconnect; $it connect $net }
    if {$wx + $wy > $dmax} { set dmax [expr {$wx + $wy}] }
    dict set ::ot_ckr_grp ot_ckr_${port}_g$ng [list $port $side]
    incr ng
  }
  puts [format "CKR: %s ring (%.1f %.1f)-(%.1f %.1f) perimeter %.0f entry (%.1f %.1f) trunk %d bufs chains +%d/-%d bufs, %d sinks -> %d local roots (max group half-perimeter %.1f um)" \
    $port $x0 $y0 $x1 $y1 $P $ex $ey $ntr $nch(p) $nch(n) [llength $sinks] $ng $dmax]
}
proc ot_ckr_ports {} {
  set re [ot_ckr_env OT_CKR_PORTS {^ck_c[0-3]r[0-3]$}]; set out {}
  foreach bt [[ord::get_db_block] getBTerms] { if {[regexp $re [$bt getName]]} { lappend out [$bt getName] } }
  return [lsort $out]
}
proc ot_ckr_leafpins {net} {   # {pin_name ins_tt} of every sequential / block clock pin below net
  set out {}; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} {
    set n [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set m [[$it getInst] getMaster]
      if {[$m isSequential] || [$m isBlock]} { lappend out [list "[[$it getInst] getName]/[[$it getMTerm] getName]" [ot_ckr_child_ins $it]]; continue }
      foreach o [[$it getInst] getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
    }
  }
  return $out
}
proc ot_ckr_arrivals {} {
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {g pl} $::ot_ckr_grp {
    set vt 0.0; set vf 0.0
    foreach pp [dict get $::ot_ckr_leaf $g] {
      lassign $pp pn ins
      set pin [get_pins -quiet $pn]; if {![llength $pin]} continue
      set x [get_property $pin arrival_max_rise]; set y [get_property $pin arrival_min_rise]
      if {$x ne "" && $x ne "INF" && $x ne "-INF" && $x + $ins > $vt} { set vt [expr {$x + $ins}] }
      if {$y ne "" && $y ne "INF" && $y ne "-INF" && $y + 0.8 * $ins > $vf} { set vf [expr {$y + 0.8 * $ins}] }
    }
    dict set a $g [list $vt $vf]
  }
  return $a
}
# pads in front of a group's local root: type A = OT_CKR_BUF with OT_CKR_PAD_HOP_UM hops (cell-heavy, FF/TT ~0.45),
# type B = the same buffer with OT_CKR_PADB_HOP_UM hops (wire-heavier, higher FF/TT): two pad types give two degrees of
# freedom per group, so TT AND FF arrivals are aligned together (one pad type can only align one corner).
proc ot_ckr_pad {g count master hop} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set inst [$blk findInst $g]; set ait [$inst findITerm A]; set net [$ait getNet]
  lassign [$inst getLocation] lx ly; set lx [expr {$lx / double($u)}]; set ly [expr {$ly / double($u)}]
  set side [lindex [dict get $::ot_ckr_grp $g] 1]
  # pads are chained root-ward: the new pads go between the existing driver and the root (the hop pattern alternates)
  $ait disconnect
  for {set i 0} {$i < $count} {incr i} {
    set p [incr ::ot_ckr_npad]
    dict incr ::ot_ckr_padk $g; set k [dict get $::ot_ckr_padk $g]
    set o [expr {($k % 2) ? $hop : 0.0}]
    if {$lx + $o > $::ot_ckr_W - 12.0 || $ly + $o > $::ot_ckr_H - 12.0} { set o [expr {-$o}] }
    if {$side eq "h"} { set x [expr {$lx + $o}]; set y $ly } else { set x $lx; set y [expr {$ly + $o}] }
    lassign [ot_ckr_mkbuf ot_ckr_pad_$p $master $x $y] c nn
    [$c findITerm A] connect $net; set net $nn
  }
  $ait connect $net
}
proc ot_ckr_med {l d} { if {![llength $l]} { return $d }; set l [lsort -real $l]; return [lindex $l [expr {[llength $l] / 2}]] }
proc ot_ckr_balance {} {
  set ::ot_ckr_npad 0; set ::ot_ckr_padk [dict create]; set ::ot_ckr_leaf [dict create]
  set blk [ord::get_db_block]
  dict for {g pl} $::ot_ckr_grp { dict set ::ot_ckr_leaf $g [ot_ckr_leafpins [[[$blk findInst $g] findITerm Y] getNet]] }
  set_propagated_clock [all_clocks]
  set rcc 0
  if {[llength [info commands ot_rc_cal_apply]]} { set rcc [ot_rc_cal_apply ckr] }
  set iters [ot_ckr_env OT_CKR_ITERS 14]; set tol [ot_ckr_env OT_CKR_TOL_PS 15]
  set mb [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx4_ASAP7_75t_R]]
  set hA [ot_ckr_env OT_CKR_PAD_HOP_UM 40.0]; set hB [ot_ckr_env OT_CKR_PADB_HOP_UM 160.0]
  # per-pad (TT, FF) delay, learned each round from groups padded with one type only
  set tA 20.0; set fA 9.0; set tB 45.0; set fB 27.0
  set prev ""; set padA [dict create]; set padB [dict create]
  for {set it 0} {$it <= $iters} {incr it} {
    set a [ot_ckr_arrivals]
    if {$prev ne ""} {
      set lA {}; set lAf {}; set lB {}; set lBf {}
      dict for {g c} $padA { if {![dict exists $padB $g]} { lappend lA [expr {([lindex [dict get $a $g] 0] - [lindex [dict get $prev $g] 0]) / $c}]; lappend lAf [expr {([lindex [dict get $a $g] 1] - [lindex [dict get $prev $g] 1]) / $c}] } }
      dict for {g c} $padB { if {![dict exists $padA $g]} { lappend lB [expr {([lindex [dict get $a $g] 0] - [lindex [dict get $prev $g] 0]) / $c}]; lappend lBf [expr {([lindex [dict get $a $g] 1] - [lindex [dict get $prev $g] 1]) / $c}] } }
      set tA [expr {max(3.0, [ot_ckr_med $lA $tA])}]; set fA [expr {max(1.0, [ot_ckr_med $lAf $fA])}]
      set tB [expr {max(3.0, [ot_ckr_med $lB $tB])}]; set fB [expr {max(1.0, [ot_ckr_med $lBf $fB])}]
    }
    set pt [dict create]; set at {}; set af {}
    dict for {g v} $a { lassign $v t f; dict lappend pt [lindex [dict get $::ot_ckr_grp $g] 0] [list $t $f]; lappend at $t; lappend af $f }
    set worst 0.0; set worstf 0.0
    dict for {p l} $pt {
      set ts [lsort -real [lmap e $l {lindex $e 0}]]; set fs [lsort -real [lmap e $l {lindex $e 1}]]
      set sp [expr {[lindex $ts end] - [lindex $ts 0]}]; set spf [expr {[lindex $fs end] - [lindex $fs 0]}]
      if {$sp > $worst} { set worst $sp }; if {$spf > $worstf} { set worstf $spf }
      puts [format "OT_CKR balance iter %d %s TT %.1f..%.1f (spread %.1f) FF-est %.1f..%.1f (spread %.1f) groups %d" \
        $it $p [lindex $ts 0] [lindex $ts end] $sp [lindex $fs 0] [lindex $fs end] $spf [llength $l]]
    }
    set at [lsort -real $at]; set af [lsort -real $af]
    set T [lindex $at end]; set F [lindex $af end]
    set allsp [expr {$T - [lindex $at 0]}]; set allf [expr {$F - [lindex $af 0]}]
    puts [format "OT_CKR balance iter %d groups %d all-port TT %.1f..%.1f (spread %.1f) FF-est %.1f..%.1f (spread %.1f) worst in-port TT %.1f FF %.1f padA %.1f/%.1f padB %.1f/%.1f ps pads %d" \
      $it [dict size $a] [lindex $at 0] $T $allsp [lindex $af 0] $F $allf $worst $worstf $tA $fA $tB $fB $::ot_ckr_npad]
    if {$it == $iters || ($allsp <= $tol && $allf <= $tol)} break
    set prev $a; set padA [dict create]; set padB [dict create]
    # TT target; FF follows when every path is the same stage (logged as FF-est).  OT_CKR_FFMIX>0 mixes the FF error in.
    set mix [ot_ckr_env OT_CKR_FFMIX 0.0]
    dict for {g v} $a {
      lassign $v t f
      set need [expr {(1.0 - $mix) * ($T - $t) + $mix * ($F - $f) * $tA / $fA - 0.5 * $tol}]
      set cA [expr {int(floor($need / $tA))}]
      if {$cA > 0} { ot_ckr_pad $g $cA $mb $hA; dict set padA $g $cA }
    }
    if {![dict size $padA] && ![dict size $padB]} break
  }
  if {$rcc} { ot_rc_cal_restore; estimate_parasitics -placement }
  detailed_placement
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_ckr_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_ckr_cts_orig
  proc clock_tree_synthesis {args} {
    set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
    set die [$blk getDieArea]
    set ::ot_ckr_W [expr {[$die xMax] / double($u)}]; set ::ot_ckr_H [expr {[$die yMax] / double($u)}]
    set ::ot_ckr_grp [dict create]; set ::ot_ckr_nblocked 0
    set ports [ot_ckr_ports]
    foreach p $ports { ot_ckr_build $p }
    puts "OT_CKR built: [dict size $::ot_ckr_grp] local roots, $::ot_ckr_nblocked buffers without a free spot within 600 um"
    detailed_placement
    set names {}
    dict for {g pl} $::ot_ckr_grp { lappend names [[[$blk findInst $g] findITerm Y] getNet] }
    set names [lmap n $names {$n getName}]
    set i [lsearch -exact $args -clk_nets]
    if {$i >= 0} { lset args [expr {$i + 1}] $names } else { lappend args -clk_nets $names }
    puts "OT_CKR CTS -clk_nets [llength $names] local nets ([llength $ports] region ports: trunk + ring chains pre-built)"
    set r [ot_ckr_cts_orig {*}$args]
    ot_ckr_balance
    return $r
  }
}
