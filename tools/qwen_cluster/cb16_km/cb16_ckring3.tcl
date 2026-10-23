# QE3-CB16 10-21 (rgxg MAIN / rgxh FALLBACK): STAGE-MATCHED multi-entry ring (successor of cb16_ckring2.tcl).
# Why (measured, rgxe gate gold2 qfd_c_b16_rgxe-20261021-124643 ck.json, child-flop referenced): TT pin-flop spread per
# region 26-48 ps (PASS) but FF 94-157 ps (FAIL): one entry per ring -> sinks near the entry need up to half a ring
# (~12 x 150-um stages) plus the child-insertion offsets in HB4xp67/BUFx2 delay-cell pads, whose FF/TT ratio (~0.5) is
# not the chain's (~0.75) -> TT-aligned trees split at FF in proportion to the padded amount (rgxf FFMIX 0.5 trades it
# back into TT: in-port TT 120 / FF-est 78).  Structure here (buffers only; same RTL, ports, clocks, flops, SDC, cycles):
#  (1) trunk port -> ring entry as before, then OT_CKR_PORTPAD stages so every port has the SAME stage count to its ring;
#  (2) OT_CKR_ENTRIES (K) equal-stage EXPRESS SPOKES from the trunk end to K equally spaced ring points (dedicated
#      chains, never tapped; shorter spokes get zig-zag stages of the SAME buffer + OT_CKR_STEP_UM wire up to the longest);
#  (3) short sub-chains (<= P/2K) from every entry; each group is tapped from its nearest entry and padded with the same
#      stage to the port's max sub-chain depth -> every clock path = the same buffer+wire stage repeated, same count;
#  (4) child-insertion offsets and residues: coarse pads = the SAME stage (zig-zag hop OT_CKR_STEP_UM, capped per
#      iteration), fine pads = BUFx2 (only the < 1-stage residue), joint TT/FF split OT_CKR_FFMIX, + post-DPL rounds.
# QKO-CB16 10-21 (rgxe MAIN / rgxf FALLBACK): cb16_ckring.tcl + (1) FAST long-haul trunk/ring stages (OT_CKR_BUF /
# OT_CKR_STEP_UM set per kit: BUFx16f every 150 um / BUFx12f every 100 um instead of BUFx4 every 30-40 um) and
# (2) post-legalisation re-balance rounds (OT_CKR_POST_ROUNDS, default 2: measure -> fine pads -> detailed_placement).
# Why (measured, rgxd gate ep5 qfd_c_b16_rgxd-20261021-093033 cts.log): the BUFx4/30-um ring chains make the
# pre-balance in-port spread 1.8-2.5 ns (iter 0) and the all-port target 3.84 ns, so ~2-3.5 ns of HB4 pads per group;
# balancer TT converged to 15-25 ps per port but FF-est stayed 90-125 ps (pad vs chain FF/TT composition x pad amount)
# and the final detailed_placement moved stacked pads up to 186 um -> measured raw per-port TT 209-311 / FF 153-216 ps.
# Both errors scale with the padded amount; fast stages cut the chain delay ~2-3x (less pad), and the post-DPL rounds
# re-measure the legalised tree. Same RTL, ports, flops, SDC, cycles.
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
  if {[ot_ckr_etm_on]} { set e [ot_ckr_etm_ins $mn $pn]; if {[llength $e]} { return [lindex $e 0] } }
  if {[string match qfd_tile_n?_rp2_romleaf_rr $mn]} {
    if {[dict exists $::ot_ckr_ins_pin $pn]} { return [dict get $::ot_ckr_ins_pin $pn] }
    return 150.0
  }
  if {[dict exists $::ot_ckr_ins $mn]} { return [dict get $::ot_ckr_ins $mn] }
  return 0.0
}
# SQC-CKE 10-22 (opt-in OT_CKR_ETM_INS=1; unset/0 = the hard-coded table above, output unchanged): hard-child clock-pin
# insertion PER CORNER from the child ETM liberty the flow loads (the *_LIB_FILES / ADDITIONAL_LIBS views, *_tt.lib with
# its *_ff.lib sibling; OT_CKR_ETM_LIBS overrides the list), per master AND per clock pin (cell_rise of
# min/max_clock_tree_path).  Why (measured, rgm gate ep9 qfd_c_b8_rgm-20261022-081054 ck.json): the table is one TT value per
# master (qfd_c_ring514 136.7 for BOTH ck_w and ck_r, whose ETM ck_r is 92.4..113.2 TT) plus per-pin TT means for the A0,
# and FF = 0.8 x TT (stations 77.3 vs ETM FF 64.9..84.6, ring ck_r 109.4 vs 74.9..94.7).  OT_CKR_ETM_REF edge (default):
# TT arrival + TT max_clock_tree_path (setup side), FF arrival + FF min_clock_tree_path (hold side); mid: (min+max)/2 at
# each corner.  Used for grouping (TT value), ot_ckr_arrivals (TT and FF) and the balance loop (no 0.8 x estimate); a pin
# without an ETM record keeps the table value and 0.8 x (counted in the OT_CKR ETM log line).
proc ot_ckr_etm_on {} { expr {[ot_ckr_env OT_CKR_ETM_INS 0] ni {0 false no off}} }
proc ot_ckr_etm_libs {} {
  set src [ot_ckr_env OT_CKR_ETM_LIBS ""]
  if {$src eq ""} {
    foreach k [lsort [array names ::env *LIB_FILES]] { lappend src {*}$::env($k) }
    if {[info exists ::env(ADDITIONAL_LIBS)]} { lappend src {*}$::env(ADDITIONAL_LIBS) }
  }
  set out {}
  foreach f $src {
    if {![regexp {^(.*)_(tt|ff)\.lib$} $f -> stem c]} continue
    foreach cc {tt ff} { set g ${stem}_$cc.lib; if {[file isfile $g] && $g ni $out} { lappend out $g } }
  }
  return $out
}
proc ot_ckr_etm_parse {f c} {
  set fh [open $f r]; set cell ""; set pin ""; set ty ""; set rise 0; set n 0
  while {[gets $fh line] >= 0} {
    if {[regexp {^\s*cell\s*\(\s*"?([^")\s]+)"?\s*\)} $line -> cell]} { set pin ""; set ty ""; set rise 0; continue }
    if {[regexp {^\s*pin\s*\(\s*"?([^")\s]+)"?\s*\)} $line -> pin]} { set ty ""; set rise 0; continue }
    if {[regexp {timing_type\s*:\s*(min|max)_clock_tree_path} $line -> t]} { set ty $t; set rise 0 }
    if {$ty eq "" || $pin eq ""} continue
    set i [string first cell_rise $line]
    if {$i >= 0} { set rise 1; set line [string range $line $i end] }
    if {$rise && [regexp {values\s*\(\s*"\s*([-0-9.eE+]+)} $line -> v]} {
      dict set ::ot_ckr_etm $cell/$pin $c,$ty $v; incr n; set ty ""; set rise 0
    }
  }
  close $fh
  return $n
}
proc ot_ckr_etm_load {} {
  if {[info exists ::ot_ckr_etm]} return
  set ::ot_ckr_etm [dict create]; set ::ot_ckr_etm_miss [dict create]
  set libs [ot_ckr_etm_libs]; set n 0
  foreach f $libs { if {[regexp {_(tt|ff)\.lib$} $f -> c]} { incr n [ot_ckr_etm_parse $f $c] } }
  puts "OT_CKR ETM: [llength $libs] child libs, $n clock_tree_path values, [dict size $::ot_ckr_etm] master/pin records, ref [ot_ckr_env OT_CKR_ETM_REF edge]"
}
# {tt ff} insertion (ps) of master/pin per OT_CKR_ETM_REF, or {} without a complete TT+FF record
proc ot_ckr_etm_ins {mn pn} {
  ot_ckr_etm_load
  set k $mn/$pn
  if {![dict exists $::ot_ckr_etm $k]} { dict incr ::ot_ckr_etm_miss $k; return {} }
  set r [dict get $::ot_ckr_etm $k]
  foreach x {tt,min tt,max ff,min ff,max} { if {![dict exists $r $x]} { dict incr ::ot_ckr_etm_miss $k; return {} } }
  if {[ot_ckr_env OT_CKR_ETM_REF edge] eq "mid"} {
    return [list [expr {0.5 * ([dict get $r tt,min] + [dict get $r tt,max])}] [expr {0.5 * ([dict get $r ff,min] + [dict get $r ff,max])}]]
  }
  return [list [dict get $r tt,max] [dict get $r ff,min]]
}
# FF reference of a sink pin: ETM FF value (opt-in) else 0.8 x the TT reference
proc ot_ckr_child_ins_ff {it tt} {
  set m [[$it getInst] getMaster]
  if {![$m isBlock]} { return 0.0 }
  set e [ot_ckr_etm_ins [$m getName] [[$it getMTerm] getName]]
  if {[llength $e]} { return [lindex $e 1] }
  return [expr {0.8 * $tt}]
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
# zig-zag stage k around ring offset s0: consecutive stages are one step apart (same buffer + same wire as a chain
# stage); every second pair shifts OT_CKR_ZZ_SHIFT_UM along the ring so pads do not stack on one site
proc ot_ckr_zz {s0 k step} { return [expr {$s0 + (($k % 2) ? 0.5 : -0.5) * $step + int(($k - 1) / 2) * [ot_ckr_env OT_CKR_ZZ_SHIFT_UM 2.7]}] }
proc ot_ckr_chainbuf {name master R s drv} {
  lassign [ot_ckr_ring_pt $R $s] x y
  lassign [ot_ckr_mkbuf $name $master $x $y] b net
  [$b findITerm A] connect $drv
  return $net
}
# geometry of one region port: ring, entry, trunk points, spokes; no db change
proc ot_ckr_plan {port} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  if {![regexp {^ck_c([0-9]+)r([0-9]+)$} $port -> c r]} { error "CKR: port name $port" }
  set a0 [$blk findInst u_t_${c}_${r}]
  if {$a0 eq "NULL"} { error "CKR: no A0 u_t_${c}_${r} for $port" }
  set bb [$a0 getBBox]; set g [ot_ckr_env OT_CKR_GAP_UM 43.2]
  set R [list [expr {max(12.0, [$bb xMin] / double($u) - $g)}] [expr {max(12.0, [$bb yMin] / double($u) - $g)}] \
              [expr {min($::ot_ckr_W - 12.0, [$bb xMax] / double($u) + $g)}] [expr {min($::ot_ckr_H - 12.0, [$bb yMax] / double($u) + $g)}]]
  lassign $R x0 y0 x1 y1; set P [expr {2 * ($x1 - $x0 + $y1 - $y0)}]
  set bt [$blk findBTerm $port]
  set pb [$bt getBBox]; set px [expr {([$pb xMin] + [$pb xMax]) / 2.0 / $u}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2.0 / $u}]
  set sE [ot_ckr_ring_s $R $px $py]; lassign [ot_ckr_ring_pt $R $sE] ex ey
  set step [ot_ckr_env OT_CKR_STEP_UM 150.0]
  set onx [expr {$px < 1.0 || $px > $::ot_ckr_W - 1.0}]
  set pts [list [list $px $py]]
  if {$onx} {
    set yr $py
    if {[ot_ckr_seg_blocked $px $py $ex $py]} {
      for {set d 10.8} {$d < 1500.0} {set d [expr {$d + 10.8}]} {
        if {![ot_ckr_seg_blocked $px [expr {$py + $d}] $ex [expr {$py + $d}]]} { set yr [expr {$py + $d}]; break }
        if {![ot_ckr_seg_blocked $px [expr {$py - $d}] $ex [expr {$py - $d}]]} { set yr [expr {$py - $d}]; break }
      }
      set xs [expr {$px < 1.0 ? $px + 20.0 : $px - 20.0}]
      lappend pts [list $xs $py] [list $xs $yr]
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
  set K [expr {max(1, int([ot_ckr_env OT_CKR_ENTRIES 8]))}]
  set ent {}; set smax 0
  for {set i 0} {$i < $K} {incr i} {
    set o [expr {$i * $P / double($K)}]; if {$o > $P / 2.0 + 1e-6} { set o [expr {$o - $P}] }
    set ns [expr {abs($o) < 1e-6 ? 0 : max(1, int(ceil(abs($o) / $step)))}]
    if {$ns > $smax} { set smax $ns }
    lappend ent [list [expr {$sE + $o}] $o $ns]
  }
  set cmax [expr {int(ceil($P / (2.0 * $K) / $step))}]
  return [dict create R $R P $P sE $sE tr $tr ent $ent smax $smax cmax $cmax tot [expr {[llength $tr] + $smax + $cmax}]]
}
proc ot_ckr_build {port Tg} {
  set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  if {[$blk findInst ot_ckr_${port}_t0] ne "NULL"} { return }
  set pl $::ot_ckr_plan($port)
  set R [dict get $pl R]; set P [dict get $pl P]; set sE [dict get $pl sE]; set cmax [dict get $pl cmax]; set smax [dict get $pl smax]
  set bt [$blk findBTerm $port]; set pnet [$bt getNet]
  set step [ot_ckr_env OT_CKR_STEP_UM 150.0]; set seg [ot_ckr_env OT_CKR_SEG_UM 120.0]; set ib [ot_ckr_env OT_CKR_INS_BIN_PS 30.0]
  set mb [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx16f_ASAP7_75t_R]]
  set mr [[ord::get_db] findMaster [ot_ckr_env OT_CKR_ROOT BUFx8_ASAP7_75t_R]]
  # sinks (before any rewiring)
  set sinks {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    if {[[[$it getInst] getMaster] isBlock]} {
      set b [$it getBBox]; set x [expr {([$b xMin] + [$b xMax]) / 2.0 / $u}]; set y [expr {([$b yMin] + [$b yMax]) / 2.0 / $u}]
    } else { lassign [[$it getInst] getLocation] x y; set x [expr {$x / double($u)}]; set y [expr {$y / double($u)}] }
    lappend sinks [list $it $x $y [ot_ckr_ring_s $R $x $y] [ot_ckr_child_ins $it]]
    if {[ot_ckr_etm_on] && [[[$it getInst] getMaster] isBlock]} {
      set k "[[[$it getInst] getMaster] getName]/[[$it getMTerm] getName]"
      if {![dict exists $::ot_ckr_etm_cmp $k]} {
        set mn [lindex [split $k /] 0]; set pn [lindex [split $k /] 1]
        set tb [expr {[string match qfd_tile_n?_rp2_romleaf_rr $mn] ? ([dict exists $::ot_ckr_ins_pin $pn] ? [dict get $::ot_ckr_ins_pin $pn] : 150.0) : ([dict exists $::ot_ckr_ins $mn] ? [dict get $::ot_ckr_ins $mn] : 0.0)}]
        dict set ::ot_ckr_etm_cmp $k [list $tb [ot_ckr_etm_ins $mn $pn]]
      }
    }
  }
  # (1) trunk + port pad stages (zig-zag on the ring around the entry)
  set drv $pnet; set k 0
  foreach p [dict get $pl tr] {
    lassign [ot_ckr_mkbuf ot_ckr_${port}_t$k $mb {*}$p] b net
    [$b findITerm A] connect $drv; set drv $net; incr k
  }
  set ntr $k
  set npp [expr {$Tg - [dict get $pl tot]}]
  for {set k 1} {$k <= $npp} {incr k} { set drv [ot_ckr_chainbuf ot_ckr_${port}_z$k $mb $R [ot_ckr_zz $sE $k $step] $drv] }
  set hub $drv
  # (2) express spokes, equalised to smax stages
  set i 0; set ents {}
  foreach e [dict get $pl ent] {
    lassign $e si o ns
    set drv $hub
    for {set k 1} {$k <= $ns} {incr k} {
      set drv [ot_ckr_chainbuf ot_ckr_${port}_s${i}_$k $mb $R [expr {$sE + $o * $k / double($ns)}] $drv]
    }
    for {set k 1} {$k <= $smax - $ns} {incr k} {
      set drv [ot_ckr_chainbuf ot_ckr_${port}_s${i}z$k $mb $R [ot_ckr_zz $si $k $step] $drv]
    }
    lappend ents [list $si $drv]
    incr i
  }
  # (3) sinks -> nearest entry; sub-chains both ways as far as needed (<= cmax stages)
  set K [llength $ents]
  array unset bye
  foreach s $sinks {
    lassign $s it x y ss ins
    set best -1; set bd 1e30; set br 0.0
    for {set i 0} {$i < $K} {incr i} {
      set rel [expr {fmod([lindex $ents $i 0] * -1.0 + $ss + 4.0 * $P, $P)}]
      if {$rel > $P / 2.0} { set rel [expr {$rel - $P}] }
      if {abs($rel) < $bd} { set bd [expr {abs($rel)}]; set best $i; set br $rel }
    }
    lappend bye($best) [list $it $x $y $br $ins]
  }
  set dlim [ot_ckr_env OT_CKR_DMAX_UM 150.0]
  set ng [dict size $::ot_ckr_grp]; set ng0 $ng; set dmax 0.0; set nsub 0; set ngp 0
  foreach i [lsort -integer [array names bye]] {
    lassign [lindex $ents $i] si edrv
    set mem $bye($i)
    set maxp 0.0; set maxn 0.0
    foreach s $mem { set o [lindex $s 3]; if {$o > $maxp} { set maxp $o }; if {-$o > $maxn} { set maxn [expr {-$o}] } }
    set ch(p,0) $edrv; set ch(n,0) $edrv
    foreach dir {p n} lim [list $maxp $maxn] sg {1 -1} {
      set n [expr {min($cmax, int(round($lim / $step)))}]
      for {set k 1} {$k <= $n} {incr k} {
        set ch($dir,$k) [ot_ckr_chainbuf ot_ckr_${port}_e${i}${dir}$k $mb $R [expr {$si + $sg * $k * $step}] $ch($dir,[expr {$k - 1}])]
        incr nsub
      }
      set nch($dir) $n
    }
    array unset grp
    foreach s $mem {
      lassign $s it x y off ins
      lappend grp("[expr {int(floor($off / $seg))}]_[expr {int(round($ins / $ib))}]") $s
    }
    set todo {}
    foreach key [lsort [array names grp]] { lappend todo $grp($key) }
    while {[llength $todo]} {
      set mem2 [lindex $todo 0]; set todo [lrange $todo 1 end]
      set xs [lsort -real [lmap s $mem2 {lindex $s 1}]]; set ys [lsort -real [lmap s $mem2 {lindex $s 2}]]
      set wx [expr {[lindex $xs end] - [lindex $xs 0]}]; set wy [expr {[lindex $ys end] - [lindex $ys 0]}]
      if {$wx + $wy > $dlim && [llength $mem2] > 1} {
        set ax [expr {$wx >= $wy ? 1 : 2}]
        set srt [lsort -real -index $ax $mem2]; set h [expr {[llength $srt] / 2}]
        lappend todo [lrange $srt 0 [expr {$h - 1}]] [lrange $srt $h end]
        continue
      }
      set co 0.0; foreach s $mem2 { set co [expr {$co + [lindex $s 3]}] }; set co [expr {$co / [llength $mem2]}]
      set dir [expr {$co >= 0 ? "p" : "n"}]; set ci [expr {min($nch($dir), int(round(abs($co) / $step)))}]
      lassign [ot_ckr_ring_pt $R [expr {$si + $co}]] rx ry side
      set g ot_ckr_${port}_g$ng
      lassign [ot_ckr_mkbuf $g $mr $rx $ry] b net
      [$b findITerm A] connect $ch($dir,$ci)
      foreach s $mem2 { set it [lindex $s 0]; $it disconnect; $it connect $net }
      if {$wx + $wy > $dmax} { set dmax [expr {$wx + $wy}] }
      dict set ::ot_ckr_grp $g [list $port $side]
      # same-stage geometric pads to the port's sub-chain depth cmax
      set gp [expr {$cmax - $ci}]
      if {$gp > 0} { ot_ckr_pad $g $gp $mb $step; incr ngp $gp }
      incr ng
    }
  }
  puts [format "CKR3: %s ring perimeter %.0f trunk %d + port pads %d, %d spokes (max %d stages), sub-chains %d bufs (depth <= %d), %d sinks -> %d local roots (max half-perimeter %.1f um), %d geometric pads; path stages %d" \
    $port $P $ntr $npp $K $smax $nsub $cmax [llength $sinks] [expr {$ng - $ng0}] $dmax $ngp $Tg]
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
      if {[$m isSequential] || [$m isBlock]} {
        set ins [ot_ckr_child_ins $it]
        if {[ot_ckr_etm_on]} {
          lappend out [list "[[$it getInst] getName]/[[$it getMTerm] getName]" $ins [ot_ckr_child_ins_ff $it $ins]]
        } else { lappend out [list "[[$it getInst] getName]/[[$it getMTerm] getName]" $ins] }
        continue
      }
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
      lassign $pp pn ins insf
      if {$insf eq ""} { set insf [expr {0.8 * $ins}] }
      set pin [get_pins -quiet $pn]; if {![llength $pin]} continue
      set x [get_property $pin arrival_max_rise]; set y [get_property $pin arrival_min_rise]
      if {$x ne "" && $x ne "INF" && $x ne "-INF" && $x + $ins > $vt} { set vt [expr {$x + $ins}] }
      if {$y ne "" && $y ne "INF" && $y ne "-INF" && $y + $insf > $vf} { set vf [expr {$y + $insf}] }
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
  # pads are chained root-ward: the new pads go between the existing driver and the root + its CTS clones
  set aits [lmap i [ot_ckr_gdrv $g] {$i findITerm A}]
  foreach x $aits { $x disconnect }
  for {set i 0} {$i < $count} {incr i} {
    set p [incr ::ot_ckr_npad]
    dict incr ::ot_ckr_padk $g; set k [dict get $::ot_ckr_padk $g]
    set o [expr {($k % 2) ? $hop : 0.0}]
    if {$lx + $o > $::ot_ckr_W - 12.0 || $ly + $o > $::ot_ckr_H - 12.0} { set o [expr {-$o}] }
    if {$side eq "h"} { set x [expr {$lx + $o}]; set y $ly } else { set x $lx; set y [expr {$ly + $o}] }
    lassign [ot_ckr_mkbuf ot_ckr_pad_$p $master $x $y] c nn
    [$c findITerm A] connect $net; set net $nn
  }
  foreach x $aits { $x connect $net }
}
# a group's drivers = its local root + every CTS clone of it (clonenet_*_<root>_clk: TritonCTS / repair_clock_nets clone
# the root onto the same input net; the clone's sinks must be measured and padded with the root)
proc ot_ckr_gdrv {g} {
  set blk [ord::get_db_block]; set root [$blk findInst $g]; set out [list $root]
  foreach it [[[$root findITerm A] getNet] getITerms] {
    set i [$it getInst]; if {$i eq $root || ![$it isInputSignal]} continue
    foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [string match "*_${g}_clk" [[$o getNet] getName]]} { lappend out $i } }
  }
  return $out
}
proc ot_ckr_med {l d} { if {![llength $l]} { return $d }; set l [lsort -real $l]; return [lindex $l [expr {[llength $l] / 2}]] }
proc ot_ckr_balance {{iters_over ""} {start_mode coarse}} {
  # cb16_ckkm's proven coarse/fine pad loop (HB4xp67 then BUFx2 at the local root, per-pad delay learned each round, 0.8
  # damping), on the corner-matched trunk/ring groups; FF-est (min arrival over scenes + 0.8 x child insertion) is logged.
  if {![info exists ::ot_ckr_npad]} { set ::ot_ckr_npad 0; set ::ot_ckr_padk [dict create] }
  set ::ot_ckr_leaf [dict create]
  set blk [ord::get_db_block]
  set ncl 0
  dict for {g pl} $::ot_ckr_grp {
    set lp {}; set dr [ot_ckr_gdrv $g]; incr ncl [expr {[llength $dr] - 1}]
    foreach i $dr { foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend lp {*}[ot_ckr_leafpins [$o getNet]] } } }
    dict set ::ot_ckr_leaf $g $lp
  }
  puts "OT_CKR balance: $ncl CTS clones of local roots folded into their groups"
  if {[ot_ckr_etm_on]} {
    puts "OT_CKR ETM balance: [dict size $::ot_ckr_etm_miss] block clock pins without a TT+FF ETM record (table + 0.8 x): [lrange [dict keys $::ot_ckr_etm_miss] 0 9]"
  }
  set_propagated_clock [all_clocks]
  set rcc 0
  if {[llength [info commands ot_rc_cal_apply]]} { set rcc [ot_rc_cal_apply ckr] }
  set iters [ot_ckr_env OT_CKR_ITERS 14]; set tol [ot_ckr_env OT_CKR_TOL_PS 15]
  if {$iters_over ne ""} { set iters $iters_over }
  set hop [ot_ckr_env OT_CKR_PAD_HOP_UM 0.0]
  # coarse pads = the SAME stage as the trunk / spokes / chains (zig-zag OT_CKR_STEP_UM hops): TT and FF move together;
  # fine pads (BUFx2, no hop) only absorb the < 1-stage residue
  set mc [[ord::get_db] findMaster [ot_ckr_env OT_CKR_BUF BUFx16f_ASAP7_75t_R]]; set mf [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
  set chop [ot_ckr_env OT_CKR_STEP_UM 150.0]; set ccap [ot_ckr_env OT_CKR_PAD_CAP 4]
  set stage [ot_ckr_env OT_CKR_STAGE_PS 45.0]; set fstage 12.0; set mode $start_mode; set prev ""; set padded [dict create]
  # OT_CKR_FFMIX m: pad need = (1-m) x TT error + m x FF error / rho (rho = pad FF/TT delay ratio, learned): m 0 aligns TT
  # only; m 0.5 splits the residual composition error between the TT (setup) and FF (hold) corners.
  set mix [ot_ckr_env OT_CKR_FFMIX 0.0]; set rho 0.5
  for {set it 0} {$it <= $iters} {incr it} {
    set a [ot_ckr_arrivals]
    if {$prev ne "" && [dict size $padded]} {
      set gl {}
      dict for {g c} $padded { lappend gl [expr {([lindex [dict get $a $g] 0] - [lindex [dict get $prev $g] 0]) / double($c)}] }
      set m [expr {max(3.0, [ot_ckr_med $gl 0])}]
      if {$mode eq "coarse"} { set stage $m } else { set fstage $m }
      set rl {}
      dict for {g c} $padded { set dt [expr {[lindex [dict get $a $g] 0] - [lindex [dict get $prev $g] 0]}]
        if {$dt > 1.0} { lappend rl [expr {([lindex [dict get $a $g] 1] - [lindex [dict get $prev $g] 1]) / $dt}] } }
      set rho [expr {min(1.0, max(0.2, [ot_ckr_med $rl $rho]))}]
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
    set at [lsort -real $at]; set af [lsort -real $af]; set T [lindex $at end]
    set allsp [expr {$T - [lindex $at 0]}]; set allf [expr {[lindex $af end] - [lindex $af 0]}]
    puts [format "OT_CKR balance iter %d (%s) groups %d all-port TT %.1f..%.1f (spread %.1f) FF-est spread %.1f worst in-port TT %.1f FF-est %.1f pad %.1f / %.1f ps pads %d" \
      $it $mode [dict size $a] [lindex $at 0] $T $allsp $allf $worst $worstf $stage $fstage $::ot_ckr_npad]
    set F [lindex $af end]
    set crit [expr {$mix > 0 ? max($allsp, $allf) : $allsp}]
    puts [format "OT_CKR balance iter %d crit %.1f rho %.2f mix %.2f" $it $crit $rho $mix]
    if {$it == $iters || $crit <= $tol} break
    if {$mode eq "coarse" && $crit < 1.6 * $stage} { set mode fine }
    set st [expr {$mode eq "coarse" ? $stage : $fstage}]
    set prev $a; set padded [dict create]
    dict for {g v} $a {
      set need [expr {(1.0 - $mix) * ($T - [lindex $v 0]) + $mix * ($F - [lindex $v 1]) / $rho}]
      set c [expr {int(floor(0.8 * ($need - 0.5 * $tol) / $st))}]
      if {$mode eq "coarse"} { set c [expr {min($c, $ccap)}] }
      if {$c > 0} { ot_ckr_pad $g $c [expr {$mode eq "coarse" ? $mc : $mf}] [expr {$mode eq "coarse" ? $chop : $hop}]; dict set padded $g $c }
    }
    if {![dict size $padded]} break
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
    if {[ot_ckr_etm_on]} { ot_ckr_etm_load; set ::ot_ckr_etm_cmp [dict create] }
    if {![info exists ::ot_ckr_npad]} { set ::ot_ckr_npad 0; set ::ot_ckr_padk [dict create] }
    set ports [ot_ckr_ports]
    set Tg 0
    foreach p $ports { set ::ot_ckr_plan($p) [ot_ckr_plan $p]; set Tg [expr {max($Tg, [dict get $::ot_ckr_plan($p) tot])}] }
    foreach p $ports { ot_ckr_build $p $Tg }
    puts "OT_CKR built: [dict size $::ot_ckr_grp] local roots, $::ot_ckr_nblocked buffers without a free spot within 600 um"
    if {[ot_ckr_etm_on]} {
      dict for {k v} $::ot_ckr_etm_cmp {
        lassign $v tb e
        if {[llength $e]} {
          puts [format "OT_CKR ETM pin %s table TT %.1f FF-est %.1f -> ETM TT %.1f FF %.1f (TT %+.1f FF %+.1f ps)" $k $tb [expr {0.8 * $tb}] {*}$e [expr {[lindex $e 0] - $tb}] [expr {[lindex $e 1] - 0.8 * $tb}]]
        } else { puts [format "OT_CKR ETM pin %s table TT %.1f: no ETM record (table kept)" $k $tb] }
      }
    }
    detailed_placement
    set names {}
    dict for {g pl} $::ot_ckr_grp { lappend names [[[$blk findInst $g] findITerm Y] getNet] }
    set names [lmap n $names {$n getName}]
    set i [lsearch -exact $args -clk_nets]
    if {$i >= 0} { lset args [expr {$i + 1}] $names } else { lappend args -clk_nets $names }
    puts "OT_CKR CTS -clk_nets [llength $names] local nets ([llength $ports] region ports: trunk + ring chains pre-built)"
    set r [ot_ckr_cts_orig {*}$args]
    ot_ckr_balance
    set nr [ot_ckr_env OT_CKR_POST_ROUNDS 2]
    for {set k 1} {$k <= $nr} {incr k} {
      puts "OT_CKR post-DPL round $k/$nr (fine)"
      ot_ckr_balance [ot_ckr_env OT_CKR_POST_ITERS 2] fine
    }
    return $r
  }
}
