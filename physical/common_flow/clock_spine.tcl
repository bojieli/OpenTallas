# CLAUDE el1011-hbm-attn 2026-10-11: pre-placed equal-delay CLOCK SPINE in place of TritonCTS for one clock port.
#
# Why (textbook class 1, hfd_attn_half_lo v10c 4_1_cts): one TritonCTS tree from ck[0] on the E face over a 1,778 x 1,264 um
# block of 85 hard banks / 2 hard quads + 158 flops: insertion 363 ps at the root banks, 1,862 ps at the far xr bank (16 CTS
# buffers + 26 -repair_clock_nets long-wire repeaters on one branch, none on another); adjacent pipe banks 474 ps apart.
# A macro-dominated block needs a planned distribution, not a sink-driven tree with post-hoc long-wire repair.
#
# What: sinks of the port net are binned into leaves (<= OT_SPINE_LEAF_N sinks in an OT_SPINE_BIN um bin); a recursive
# bisection tree joins the leaves (node = leaf centroid); the root is fed from the port by a repeated trunk; every edge is
# an L path chosen to avoid macros, repeated every <= OT_SPINE_SEG um; buffers sit on legal sites outside macros/blockages,
# on sites no placed cell uses (no overlap, no late flop displacement; check_placement verified after insertion),
# FIRM + dont_touch, every spine net is CLOCK (clk_net_protect keeps resizer off it).  Leaves are then padded to equal
# MEASURED arrival (STA, placement parasitics), OT_SPINE_ITERS rounds.  TritonCTS is not run for this clock.
# Chain it FIRST in OT_CTS_FIX_HOOKS (it wraps clock_tree_synthesis; other hooks wrap it).  Knobs (env): OT_SPINE_PORT
# (default ck[0]), OT_SPINE_MACRO_LEAF 0, OT_SPINE_SEG 150, OT_SPINE_BIN 60, OT_SPINE_LEAF_N 8, OT_SPINE_HALO 3, OT_SPINE_CELL BUFx24_ASAP7_75t_R,
# OT_SPINE_ITERS 3, OT_SPINE_SYM 0 (symmetric insertion-aware topology, see ot_sp_sym_build).  Functional netlist unchanged (buffers only).

proc ot_sp_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }

proc ot_sp_blocked {x0 y0 x1 y1} {
  if {$x0 < $::ot_sp_cx0 || $x1 > $::ot_sp_cx1 || $y0 < $::ot_sp_cy0 || $y1 > $::ot_sp_cy1} { return 1 }
  foreach r $::ot_sp_obs {
    lassign $r a0 b0 a1 b1
    if {$x1 > $a0 && $x0 < $a1 && $y1 > $b0 && $y0 < $b1} { return 1 }
  }
  return 0
}
proc ot_sp_ptblocked {x y} { return [ot_sp_blocked $x $y [expr {$x + 1}] [expr {$y + 1}]] }

# nearest point whose cell footprint is free (square rings, 2 um steps, 16 samples per ring)
proc ot_sp_free {x y} {
  set w $::ot_sp_cw; set h $::ot_sp_rh; set u $::ot_sp_dbu
  if {![ot_sp_blocked $x $y [expr {$x + $w}] [expr {$y + $h}]]} { return [list $x $y] }
  for {set r 2} {$r <= 600} {incr r 2} {
    set d [expr {$r * $u}]; set e [expr {$d / 2}]
    foreach {dx dy} [list $d 0 -$d 0 0 $d 0 -$d $d $d -$d $d $d -$d -$d -$d $d $e -$d $e $d -$e -$d -$e $e $d -$e $d $e -$d -$e -$d] {
      set nx [expr {$x + $dx}]; set ny [expr {$y + $dy}]
      if {![ot_sp_blocked $nx $ny [expr {$nx + $w}] [expr {$ny + $h}]]} { return [list $nx $ny] }
    }
  }
  return [list $x $y]
}

# is the w-wide footprint at (cx, cy) inside one row segment, outside macros/hard blockages, and on sites no other cell uses?
proc ot_sp_fits {cx cy nsite} {
  set sw $::ot_sp_sw
  for {set s 0} {$s < $nsite} {incr s} { if {[dict exists $::ot_sp_used "$cy,[expr {$cx + $s * $sw}]"]} { return 0 } }
  if {![dict exists $::ot_sp_rowseg $cy]} { return 0 }
  set in 0; set x1 [expr {$cx + $nsite * $sw}]
  foreach sg [dict get $::ot_sp_rowseg $cy] { lassign $sg a b; if {$cx >= $a && $x1 <= $b} { set in 1; break } }
  if {!$in} { return 0 }
  return [expr {![ot_sp_blocked $cx $cy $x1 [expr {$cy + $::ot_sp_rh}]]}]
}

# Snap to the nearest FREE legal footprint: sites taken by ANY placed cell (movable flops/logic included, not only fixed
# cells) or by another spine cell are excluded, so an inserted spine buffer never overlaps an existing instance and never
# needs detailed placement to displace a flop after the fact (hcoll-port-tile11 g11a: 44 DPL-0033 overlaps, PLACED flops
# under FIRM clkbuf_sp_* -- the occupancy map used to hold only FIRM/LOCKED/FIXED cells).  Search: rows in order of
# |dr|, and within a row outward site by site; cost = |dx| + |dy|, stop once a row's dy alone exceeds the best cost.
proc ot_sp_search {x y R D} {
  set sw $::ot_sp_sw; set rh $::ot_sp_rh; set w $::ot_sp_cw
  set ry [expr {$::ot_sp_ry0 + int(round(double($y - $::ot_sp_ry0) / $rh)) * $rh}]
  set sx [expr {$::ot_sp_rx0 + int(round(double($x - $::ot_sp_rx0) / $sw)) * $sw}]
  set nsite [expr {int(ceil(double($w) / $sw))}]
  set best ""; set bc 1e18
  for {set k 0} {$k <= 2 * $D} {incr k} {
    set dr [expr {($k + 1) / 2 * ($k % 2 ? 1 : -1)}]
    set rc [expr {abs($dr) * $rh}]
    if {$rc >= $bc} break
    set cy [expr {$ry + $dr * $rh}]
    if {![dict exists $::ot_sp_rowseg $cy]} continue
    for {set d 0} {$d <= $R} {incr d} {
      if {$rc + $d * $sw >= $bc} break
      foreach sg {1 -1} {
        set cx [expr {$sx + $sg * $d * $sw}]
        if {[ot_sp_fits $cx $cy $nsite]} { set best [list $cx $cy]; set bc [expr {$rc + $d * $sw}]; break }
      }
      if {$best ne "" && [lindex $best 1] == $cy} break
    }
  }
  return $best
}
# Crowded targets (bgq28 s81vm-bgq28-f9a57959c-ck pd45/l8: a 4,144-flop pin-flop row packed along the S face; the old
# fallback stepped the target +x 10 um at a time along that same packed band to the E edge -> 'no legal site'): widen
# the nearest-free-footprint search window (rows x4, sites x2 per step, up to 192x the rows) around the SAME target
# before falling back to moving the target, so the cell lands on the closest free footprint in any direction.
proc ot_sp_legal {x y} {
  set best ""
  for {set m 1} {$m <= 256} {set m [expr {$m * 4}]} {
    set best [ot_sp_search $x $y [expr {$::ot_sp_rsites * min($m, 8)}] [expr {$::ot_sp_rrows * $m}]]
    if {$best ne ""} break
  }
  if {$best ne ""} {
    lassign $best cx cy
    set nsite [expr {int(ceil(double($::ot_sp_cw) / $::ot_sp_sw))}]
    # spine cells keep a one-site gap to each other (pin access between adjacent x24 buffers)
    for {set s -1} {$s <= $nsite} {incr s} { dict set ::ot_sp_used "$cy,[expr {$cx + $s * $::ot_sp_sw}]" 1 }
    return $best
  }
  # still nothing: move the target 10 um and retry
  if {[incr ::ot_sp_retry] < 40} {
    lassign [ot_sp_free [expr {$x + 10 * $::ot_sp_dbu}] $y] fx fy
    set r [ot_sp_legal $fx $fy]; set ::ot_sp_retry 0; return $r
  }
  error "OT_SPINE: no legal site near $x $y"
}

# Every spine cell was put on free sites, so the design must pass check_placement exactly as it did before insertion.
# Guard (should never fire): if it does not, legalise the movable cells around the FIRM spine (detailed_placement moves
# only PLACED instances) and re-check, so CTS never continues on an illegal placement.
proc ot_sp_check_legal {} {
  if {[catch {check_placement} e] == 0} { puts "OT_SPINE legal: check_placement clean after $::ot_sp_nbuf spine cells"; return }
  puts "OT_SPINE WARNING: check_placement failed after spine insertion ($e); legalising movable cells around the spine"
  detailed_placement
  check_placement
  puts "OT_SPINE legal: check_placement clean after detailed_placement"
}

proc ot_sp_buf {name x y innet {m ""}} {
  if {$m eq ""} { set m $::ot_sp_m }
  set ::ot_sp_cw [$m getWidth]
  set ::ot_sp_retry 0
  lassign [ot_sp_legal $x $y] lx ly
  set b [odb::dbInst_create $::ot_sp_blk $m $name]
  set o R0
  if {[dict exists $::ot_sp_rowor $ly]} { set o [dict get $::ot_sp_rowor $ly] }
  $b setOrient $o
  $b setLocation $lx $ly
  $b setPlacementStatus FIRM
  [$b findITerm $::ot_sp_in] connect $innet
  set on [odb::dbNet_create $::ot_sp_blk "${name}_net"]
  $on setSigType CLOCK
  [$b findITerm $::ot_sp_out] connect $on
  incr ::ot_sp_nbuf
  lappend ::ot_sp_insts $b
  return [list $on $lx $ly $b]
}

# L path from p to q avoiding macros where possible; returns the repeater points (exclusive of p and q)
proc ot_sp_path {px py qx qy} {
  set seg $::ot_sp_seg
  set best ""; set bestbad 1e9
  foreach c [list [list $qx $py] [list $px $qy]] {
    lassign $c kx ky
    set len [expr {abs($kx - $px) + abs($ky - $py) + abs($qx - $kx) + abs($qy - $ky)}]
    set bad 0
    set n [expr {max(1, int($len / (5 * $::ot_sp_dbu)))}]
    for {set i 0} {$i <= $n} {incr i} {
      lassign [ot_sp_along $px $py $kx $ky $qx $qy [expr {$len * $i / double($n)}]] sx sy
      if {[ot_sp_ptblocked $sx $sy]} { incr bad }
    }
    if {$bad < $bestbad} { set bestbad $bad; set best [list $kx $ky $len] }
  }
  lassign $best kx ky len
  set k [expr {max(0, int(ceil(double($len) / $seg)) - 1)}]
  set pts {}
  for {set i 1} {$i <= $k} {incr i} {
    lassign [ot_sp_along $px $py $kx $ky $qx $qy [expr {$len * $i / double($k + 1)}]] sx sy
    lappend pts [ot_sp_free [expr {int($sx)}] [expr {int($sy)}]]
  }
  return [list $pts $len]
}
proc ot_sp_along {px py kx ky qx qy d} {
  set l1 [expr {abs($kx - $px) + abs($ky - $py)}]
  if {$d <= $l1} {
    if {$l1 == 0} { return [list $px $py] }
    set f [expr {$d / double($l1)}]
    return [list [expr {$px + ($kx - $px) * $f}] [expr {$py + ($ky - $py) * $f}]]
  }
  set l2 [expr {abs($qx - $kx) + abs($qy - $ky)}]
  if {$l2 == 0} { return [list $qx $qy] }
  set f [expr {($d - $l1) / double($l2)}]
  return [list [expr {$kx + ($qx - $kx) * $f}] [expr {$ky + ($qy - $ky) * $f}]]
}

# recursive bisection over leaf ids; returns a node id (leaf ids are L<i>, internal N<j>)
proc ot_sp_split {ids} {
  if {[llength $ids] == 1} { return [lindex $ids 0] }
  set xs {}; set ys {}
  foreach i $ids { lassign [dict get $::ot_sp_pos $i] x y; lappend xs $x; lappend ys $y }
  set ax [expr {[tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs] >= [tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys] ? 0 : 1}]
  set srt [lsort -command [list ot_sp_cmp $ax] $ids]
  set h [expr {[llength $srt] / 2}]
  set a [ot_sp_split [lrange $srt 0 [expr {$h - 1}]]]
  set b [ot_sp_split [lrange $srt $h end]]
  set n "N[incr ::ot_sp_nn]"
  set sx 0.0; set sy 0.0; set sw 0
  foreach i $ids { lassign [dict get $::ot_sp_pos $i] x y; set c [dict get $::ot_sp_cnt $i]; set sx [expr {$sx + $x * $c}]; set sy [expr {$sy + $y * $c}]; incr sw $c }
  dict set ::ot_sp_pos $n [ot_sp_free [expr {int($sx / $sw)}] [expr {int($sy / $sw)}]]
  dict set ::ot_sp_cnt $n $sw
  dict set ::ot_sp_kids $n [list $a $b]
  return $n
}
proc ot_sp_cmp {ax a b} {
  set va [lindex [dict get $::ot_sp_pos $a] $ax]; set vb [lindex [dict get $::ot_sp_pos $b] $ax]
  if {$va < $vb} { return -1 } elseif {$va > $vb} { return 1 }; return 0
}

# ---- OT_SPINE_SYM=1 (el1013-smh-r11 2026-10-13): symmetric, insertion-aware topology ------------------------------------
# Why (SM tile cluster smh_tile_eg r10, 630 x 1,253 um, 979 sinks, 12 hard children with 196-526 ps of own insertion):
# the count-bisection tree put one BUFx24 at every one of its 8 levels at the count-weighted centroid (zig-zag, 23 buffer
# stages root to leaf) and made the slowest hard child (pt_w, 525.9 ps inside) a leaf at full depth: its pin arrived at
# 1,317 ps, every other leaf was padded up to 1,843-1,901 ps with 2,073 delay cells (17-21 a leaf), and the pad chains
# (cell delay) did not track the wire-dominated trunk at the fast corner: 28.8 ps spread at TT became 102 ps at FF.
# What: (1) the flop leaves get a bisection tree whose nodes sit at the CENTRE of their leaves' bounding box (both
# children see the same span) and whose short levels are collapsed into their parent (no buffer for an edge shorter
# than OT_SPINE_SYM_MERGE um, fanout <= OT_SPINE_SYM_FAN); (2) a top buffer sits at the root (the ICG output); (3) each
# leaf that carries its own insertion (kit dict ::ot_ref_child_ins / ::ot_sp_child_ins: master -> ps) taps the tree at
# the nearest node that still lets it arrive no later than the latest flop leaf -- at the top buffer if none does -- so
# the trunk a slow child sees is as short as its own insertion requires and the padding left is the true imbalance.
proc ot_sp_split_bb {ids} {
  if {[llength $ids] == 1} { return [lindex $ids 0] }
  set xs {}; set ys {}
  foreach i $ids { lassign [dict get $::ot_sp_pos $i] x y; lappend xs $x; lappend ys $y }
  set x0 [tcl::mathfunc::min {*}$xs]; set x1 [tcl::mathfunc::max {*}$xs]
  set y0 [tcl::mathfunc::min {*}$ys]; set y1 [tcl::mathfunc::max {*}$ys]
  set ax [expr {$x1 - $x0 >= $y1 - $y0 ? 0 : 1}]
  set srt [lsort -command [list ot_sp_cmp $ax] $ids]
  set h [expr {[llength $srt] / 2}]
  set a [ot_sp_split_bb [lrange $srt 0 [expr {$h - 1}]]]
  set b [ot_sp_split_bb [lrange $srt $h end]]
  set n "N[incr ::ot_sp_nn]"
  set sw 0; foreach i $ids { incr sw [dict get $::ot_sp_cnt $i] }
  dict set ::ot_sp_pos $n [ot_sp_free [expr {int(($x0 + $x1) / 2)}] [expr {int(($y0 + $y1) / 2)}]]
  dict set ::ot_sp_cnt $n $sw
  dict set ::ot_sp_kids $n [list $a $b]
  return $n
}
proc ot_sp_dist {a b} {
  lassign [dict get $::ot_sp_pos $a] ax ay; lassign [dict get $::ot_sp_pos $b] bx by
  return [expr {abs($ax - $bx) + abs($ay - $by)}]
}
# splice out internal nodes closer than `merge` (dbu) to their parent while the parent's fanout stays <= fan
proc ot_sp_collapse {n merge fan} {
  if {![dict exists $::ot_sp_kids $n]} return
  foreach k [dict get $::ot_sp_kids $n] { ot_sp_collapse $k $merge $fan }
  set again 1
  while {$again} {
    set again 0; set kids [dict get $::ot_sp_kids $n]; set out {}
    foreach k $kids {
      if {!$again && [dict exists $::ot_sp_kids $k] && [ot_sp_dist $n $k] < $merge
          && [llength $kids] - 1 + [llength [dict get $::ot_sp_kids $k]] <= $fan} {
        lappend out {*}[dict get $::ot_sp_kids $k]
        dict unset ::ot_sp_kids $k; dict unset ::ot_sp_pos $k; dict unset ::ot_sp_cnt $k
        set again 1
      } else { lappend out $k }
    }
    dict set ::ot_sp_kids $n $out
  }
}
# estimated arrival (ps) at every node's buffer output: kw ps per dbu of trunk + kb ps per buffer
proc ot_sp_est {n t kw kb} {
  dict set ::ot_sp_est_t $n $t
  if {![dict exists $::ot_sp_kids $n]} return
  foreach k [dict get $::ot_sp_kids $n] { ot_sp_est $k [expr {$t + [ot_sp_dist $n $k] * $kw + $kb}] $kw $kb }
}
# ids: leaf ids; lins: leaf id -> own insertion (ps, absent / 0 for flop leaves); (rx, ry): the root point.  Returns the top node.
proc ot_sp_sym_build {ids lins rx ry} {
  set u $::ot_sp_dbu
  set merge [expr {[ot_sp_env OT_SPINE_SYM_MERGE 40] * $u}]
  set fan [ot_sp_env OT_SPINE_SYM_FAN 8]
  set kb [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  set kw [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43] / double($u)}]
  set late {}; set early {}
  foreach i $ids { if {[dict exists $lins $i] && [dict get $lins $i] > 0} { lappend early $i } else { lappend late $i } }
  if {![llength $late]} { set late $early; set early {} }
  set sub [ot_sp_split_bb $late]
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  set sw 0; foreach i $ids { incr sw [dict get $::ot_sp_cnt $i] }
  dict set ::ot_sp_cnt $top $sw
  dict set ::ot_sp_kids $top [list $sub]
  ot_sp_collapse $top $merge $fan
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top $kb $kw $kb
  set latest 0.0
  foreach i $late { set v [dict get $::ot_sp_est_t $i]; if {$v > $latest} { set latest $v } }
  set ntop 0
  # slowest child first: it takes the earliest tap it needs before the others are placed
  foreach e [lsort -command [list ot_sp_cmp_ins $lins] $early] {
    set o [dict get $lins $e]
    set best ""; set bd 1e30; set fall ""; set ft 1e30
    foreach n [dict keys $::ot_sp_kids] {
      if {[llength [dict get $::ot_sp_kids $n]] >= $fan && $n ne $top} continue
      set d [ot_sp_dist $n $e]
      set t [expr {[dict get $::ot_sp_est_t $n] + $d * $kw + $kb}]
      if {$t + $o <= $latest && $d < $bd} { set bd $d; set best $n }
      if {$t < $ft} { set ft $t; set fall $n }
    }
    if {$best eq ""} { set best $fall; incr ntop }
    dict lappend ::ot_sp_kids $best $e
    dict set ::ot_sp_est_t $e [expr {[dict get $::ot_sp_est_t $best] + [ot_sp_dist $best $e] * $kw + $kb}]
  }
  puts [format "OT_SPINE sym: %d flop leaves, %d insertion leaves (%d on their earliest tap), %d tree nodes, estimated latest flop leaf %.0f ps" \
          [llength $late] [llength $early] $ntop [dict size $::ot_sp_kids] $latest]
  return $top
}
proc ot_sp_cmp_ins {lins a b} {
  set va [dict get $lins $a]; set vb [dict get $lins $b]
  if {$va > $vb} { return -1 } elseif {$va < $vb} { return 1 }; return 0
}

# build node n's buffer fed by innet from (px,py); recurse
proc ot_sp_emit {n innet px py} {
  lassign [dict get $::ot_sp_pos $n] nx ny
  lassign [ot_sp_path $px $py $nx $ny] pts len
  set net $innet; set k 0
  foreach p $pts { lassign [ot_sp_buf "${::ot_sp_prefix}${n}_r[incr k]" {*}$p $net] net }
  lassign [ot_sp_buf "${::ot_sp_prefix}${n}" $nx $ny $net] onet lx ly
  if {[dict exists $::ot_sp_kids $n]} {
    foreach c [dict get $::ot_sp_kids $n] { ot_sp_emit $c $onet $lx $ly }
  } else {
    dict set ::ot_sp_leafnet $n $onet
    foreach it [dict get $::ot_sp_members $n] { $it disconnect; $it connect $onet }
  }
}

# Opt-in safe balancing keeps a measured best clock topology.  Rollback reconnects
# each surviving leaf to its old input net, then deletes ONLY subsequently added
# pad instances/nets.  No ODB reload: all surviving Tcl object handles stay valid.
proc ot_sp_checkpoint {} {
  set inputs [dict create]
  # every node that can carry pads (leaves; all tree nodes under OT_SPINE_TREE_PAD)
  foreach n [dict keys $::ot_sp_npad] {
    set b [$::ot_sp_blk findInst "${::ot_sp_prefix}${n}"]
    if {$b eq "NULL"} continue
    dict set inputs $n [[$b findITerm $::ot_sp_in] getNet]
  }
  return [dict create inputs $inputs insts $::ot_sp_insts nbuf $::ot_sp_nbuf npad $::ot_sp_npad used $::ot_sp_used]
}
proc ot_sp_restore {saved} {
  dict for {n net} [dict get $saved inputs] {
    set b [$::ot_sp_blk findInst "${::ot_sp_prefix}${n}"]
    set p [$b findITerm $::ot_sp_in]
    $p disconnect; $p connect $net
  }
  set added [lrange $::ot_sp_insts [llength [dict get $saved insts]] end]
  set nets {}
  foreach b $added { lappend nets [[$b findITerm $::ot_sp_out] getNet] }
  # Destroy instances first: no net is destroyed while a pad pin still references it.
  foreach b [lreverse $added] { odb::dbInst_destroy $b }
  foreach net [lreverse $nets] { odb::dbNet_destroy $net }
  set ::ot_sp_insts [dict get $saved insts]
  set ::ot_sp_nbuf [dict get $saved nbuf]
  set ::ot_sp_npad [dict get $saved npad]
  set ::ot_sp_used [dict get $saved used]
  puts "OT_SPINE restored best checkpoint; removed [llength $added] pad cells"
}
proc ot_sp_keep_best {a} {
  set vals [dict values $a]
  set spread [expr {[tcl::mathfunc::max {*}$vals] - [tcl::mathfunc::min {*}$vals]}]
  if {![info exists ::ot_sp_best_spread] || $spread < $::ot_sp_best_spread} {
    set ::ot_sp_best_spread $spread
    set ::ot_sp_best_state [ot_sp_checkpoint]
    return 1
  }
  if {$spread > $::ot_sp_best_spread + 0.001} {
    puts "OT_SPINE overshoot $spread ps vs best $::ot_sp_best_spread ps; restoring measured best"
    ot_sp_restore $::ot_sp_best_state
    return 0
  }
  return 1
}

# insert `count` pad buffers in front of leaf n's buffer (between its driver net and its A pin)
proc ot_sp_pad {n count} {
  set lb [$::ot_sp_blk findInst "${::ot_sp_prefix}${n}"]
  set ait [$lb findITerm $::ot_sp_in]
  set net [$ait getNet]
  set loc [$lb getLocation]; lassign $loc lx ly
  $ait disconnect
  set p [dict get $::ot_sp_npad $n]
  for {set i 0} {$i < $count} {incr i} {
    lassign [ot_sp_buf "${::ot_sp_prefix}${n}_p[incr p]" $lx $ly $net $::ot_sp_pm] net
  }
  dict set ::ot_sp_npad $n $p
  $ait connect $net
}

# Opt-in subtree-common padding (OT_SPINE_TREE_PAD=1).  Per-leaf padding spends one pad chain per leaf even when a whole
# subtree is early by the same amount: qw_h3/qw_h3p (777.6 x 691.2 um, 4,05x leaves, 31,912 sinks) grew from 8,1xx to
# 165,891 / 190,931 spine cells, the pads no longer found sites near their leaves, their wire delay overshot the measured
# pad delay, and the latest arrival ran from 1,413 to 4,428 ps (spread 136 -> 1,200 ps, hold -764.7 ps).  Here the delay a
# subtree needs in common (the minimum need of its leaves) is inserted ONCE at the subtree's node buffer and only the
# remainder goes further down, so the pad count follows the tree imbalance, not the leaf count.
proc ot_sp_tree_min {n need} {
  if {[dict exists $::ot_sp_kids $n]} {
    set m ""
    foreach c [dict get $::ot_sp_kids $n] { set v [ot_sp_tree_min $c $need]; if {$m eq "" || $v < $m} { set m $v } }
  } else {
    set m [expr {[dict exists $need $n] ? max(0, [dict get $need $n]) : 0}]
  }
  dict set ::ot_sp_tmin $n $m
  return $m
}
proc ot_sp_tree_apply {n above} {
  set c [expr {[dict get $::ot_sp_tmin $n] - $above}]
  if {$c > 0} { ot_sp_pad $n $c; incr ::ot_sp_tpads $c }
  if {[dict exists $::ot_sp_kids $n]} {
    foreach k [dict get $::ot_sp_kids $n] { ot_sp_tree_apply $k [dict get $::ot_sp_tmin $n] }
  }
}
proc ot_sp_tree_pad {root need} {
  set ::ot_sp_tmin [dict create]; set ::ot_sp_tpads 0
  ot_sp_tree_min $root $need
  ot_sp_tree_apply $root 0
  return $::ot_sp_tpads
}
proc ot_sp_leaf_arrivals {} {
  estimate_parasitics -placement
  # build the timing graph for the new cells before reading pin properties (pinArrival on an un-graphed pin segfaults)
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {n net} $::ot_sp_leafnet {
    # latest SINK of the leaf (leaf loads differ: bank clock pins vs flops)
    set v 0.0
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {
      set x [get_property $pin arrival_max_rise]
      if {$x ne "" && $x ne "INF" && $x ne "-INF" && $x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}

proc ot_clock_spine {{requested_port ""} {prefix clkbuf_sp_}} {
  set ::ot_sp_prefix $prefix
  set ::ot_sp_blk [ord::get_db_block]
  set blk $::ot_sp_blk
  set ::ot_sp_dbu [$blk getDbUnitsPerMicron]
  set u $::ot_sp_dbu
  set port $requested_port
  if {$port eq ""} { set port [ot_sp_env OT_SPINE_PORT {ck[0]}] }
  set bt [$blk findBTerm $port]
  # s81-spwfc 2026-10-13: a [0:0] clock port stays "ck[0]" in a wires-only cluster netlist and becomes "ck" in a
  # flattened leaf; ref_tile passes the base name.  Try the other spelling before giving up (s81sp_capc_cl gate:
  # "OT_SPINE skipped: no port ck", plain TritonCTS, insertion 1,507 ps).
  if {$bt eq "NULL" || $bt eq ""} {
    if {[regexp {^(.*)\[0\]$} $port -> base]} { set alt $base } else { set alt [format {%s[0]} $port] }
    set bt2 [$blk findBTerm $alt]
    if {$bt2 ne "NULL" && $bt2 ne ""} { puts "OT_SPINE port $port not found, using $alt"; set bt $bt2; set port $alt }
  }
  if {$bt eq "NULL" || $bt eq ""} { puts "OT_SPINE skipped: no port $port"; return 0 }
  set net0 [$bt getNet]
  # OT_SPINE_THROUGH_ICG=1 (el1011-hbm-smt 2026-10-12): the port clock enters ONE tile clock gate (ICG*, e.g. the SM tile's
  # ot_cg_tile) that clocks everything else.  A spine on the port net would see only the ICG and its few enable flops and
  # leave the whole gated network without a tree; build the spine on the ICG's GCLK net instead, rooted at the ICG output.
  # The port net keeps the ICG + its enable registers (local, beside the clk / cgi pins), so the ENA check stays balanced.
  set ::ot_sp_root_xy ""
  if {[ot_sp_env OT_SPINE_THROUGH_ICG 0] eq "1"} {
    set icgs {}
    foreach it [$net0 getITerms] {
      if {[$it getIoType] ne "INPUT"} continue
      if {[string match ICG* [[[$it getInst] getMaster] getName]]} { lappend icgs [$it getInst] }
    }
    if {[llength $icgs] != 1} { error "OT_SPINE_THROUGH_ICG: port $port drives [llength $icgs] ICG cells (need exactly 1)" }
    set g [lindex $icgs 0]
    # the ICG and every other cell on the port net (its enable registers) move next to the clock pin below: placed by the
    # global placer at the centroid of the whole gated network they sat ~600 um from the pin on an unbuffered port net
    # (SM tile cluster gate: leaf arrivals 1.3-2.7 ns before padding, 3.5 ns after)
    set ::ot_sp_icg_move {}
    foreach it [$net0 getITerms] {
      set i [$it getInst]
      if {![[$i getMaster] isBlock] && [lsearch -exact $::ot_sp_icg_move $i] < 0} { lappend ::ot_sp_icg_move $i }
    }
    set ::ot_sp_icg_port $::ot_sp_icg_move
    # + their local logic (counter / enable cone): cells within 6 net hops over nets of fanout <= 16, capped at 400 cells
    set front $::ot_sp_icg_move
    for {set d 0} {$d < 6 && [llength $front]} {incr d} {
      set nxt {}
      foreach i $front {
        foreach it [$i getITerms] {
          set n [$it getNet]
          if {$n eq "NULL" || $n eq ""} continue
          if {[$n getSigType] in {POWER GROUND CLOCK} || $n eq $net0} continue
          if {[llength [$n getITerms]] > 17 || [llength [$n getBTerms]] > 0 && [llength [$n getITerms]] > 4} continue
          foreach jt [$n getITerms] {
            set j [$jt getInst]
            if {[[$j getMaster] isBlock] || [lsearch -exact $::ot_sp_icg_move $j] >= 0} continue
            if {[llength $::ot_sp_icg_move] >= 400} break
            lappend ::ot_sp_icg_move $j; lappend nxt $j
          }
        }
      }
      set front $nxt
    }
    set ::ot_sp_icg $g
    set gt [$g findITerm GCLK]
    set net0 [$gt getNet]
    lassign [$gt getAvgXY] ok gx gy
    if {!$ok} { lassign [$g getLocation] gx gy }
    set ::ot_sp_root_xy [list $gx $gy]
    puts "OT_SPINE through ICG [$g getName]: spine on net [$net0 getName]"
  }
  set ::ot_sp_seg [expr {int([ot_sp_env OT_SPINE_SEG 150] * $u)}]
  set bin [expr {[ot_sp_env OT_SPINE_BIN 60] * $u}]
  set lmax [ot_sp_env OT_SPINE_LEAF_N 8]
  set halo [expr {int([ot_sp_env OT_SPINE_HALO 3] * $u)}]
  set ::ot_sp_m [[ord::get_db] findMaster [ot_sp_env OT_SPINE_CELL BUFx24_ASAP7_75t_R]]
  set ::ot_sp_in A; set ::ot_sp_out Y
  set ::ot_sp_cw [$::ot_sp_m getWidth]
  set ::ot_sp_pmc [[ord::get_db] findMaster [ot_sp_env OT_SPINE_PAD_CELL HB4xp67_ASAP7_75t_R]]
  set ::ot_sp_pmf [[ord::get_db] findMaster [ot_sp_env OT_SPINE_FINE_CELL BUFx2_ASAP7_75t_R]]
  if {$::ot_sp_pmc eq "NULL" || $::ot_sp_pmc eq ""} { set ::ot_sp_pmc $::ot_sp_m }
  if {$::ot_sp_pmf eq "NULL" || $::ot_sp_pmf eq ""} { set ::ot_sp_pmf $::ot_sp_m }
  set ::ot_sp_pm $::ot_sp_pmc
  set core [$blk getCoreArea]
  set ::ot_sp_cx0 [$core xMin]; set ::ot_sp_cy0 [$core yMin]; set ::ot_sp_cx1 [$core xMax]; set ::ot_sp_cy1 [$core yMax]
  set ::ot_sp_obs {}
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} {
      set b [$i getBBox]
      lappend ::ot_sp_obs [list [expr {[$b xMin] - $halo}] [expr {[$b yMin] - $halo}] [expr {[$b xMax] + $halo}] [expr {[$b yMax] + $halo}]]
    }
  }
  # only HARD placement blockages exclude spine cells: soft / partial-density blockages are global-placer guidance (e.g. the
  # hcoll pin-flop channel guides cover every face strip beside the SRAM columns; treating them as hard left no legal site
  # for the west-face leaves -> 'no legal site', hcoll-port-tile10 g10a/g10b).  Spine cells are FIRM, so legal there.
  foreach g [$blk getBlockages] {
    if {[$g isSoft]} continue
    if {[catch {$g getMaxDensity} md] == 0 && $md > 0 && $md < 100} continue
    set b [$g getBBox]; lappend ::ot_sp_obs [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  set ::ot_sp_rowor [dict create]; set ::ot_sp_rowseg [dict create]; set ::ot_sp_ry0 ""; set ::ot_sp_rx0 ""
  foreach r [$blk getRows] {
    lassign [$r getOrigin] ox oy
    if {$::ot_sp_ry0 eq "" || $oy < $::ot_sp_ry0} { set ::ot_sp_ry0 $oy }
    if {$::ot_sp_rx0 eq "" || $ox < $::ot_sp_rx0} { set ::ot_sp_rx0 $ox }
    dict set ::ot_sp_rowor $oy [$r getOrient]
    set rb [$r getBBox]; dict lappend ::ot_sp_rowseg $oy [list [$rb xMin] [$rb xMax]]
    set ::ot_sp_sw [[$r getSite] getWidth]; set ::ot_sp_rh [[$r getSite] getHeight]
  }
  set ::ot_sp_used [dict create]; set ::ot_sp_nbuf 0; set ::ot_sp_nn 0; set ::ot_sp_insts {}
  set ::ot_sp_rsites [ot_sp_env OT_SPINE_SEARCH_SITES 600]; set ::ot_sp_rrows [ot_sp_env OT_SPINE_SEARCH_ROWS 12]
  # every placed standard cell (fixed AND movable) keeps its sites: spine cells go on free sites only
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} continue
    if {![$i isPlaced]} continue
    set b [$i getBBox]
    for {set y [$b yMin]} {$y < [$b yMax]} {incr y $::ot_sp_rh} {
      for {set x [$b xMin]} {$x < [$b xMax]} {incr x $::ot_sp_sw} { dict set ::ot_sp_used "$y,$x" 1 }
    }
  }
  if {$::ot_sp_root_xy ne ""} {
    set pb0 [$bt getBBox]
    set qx [expr {([$pb0 xMin] + [$pb0 xMax]) / 2}]; set qy [expr {([$pb0 yMin] + [$pb0 yMax]) / 2}]
    set qx [expr {min(max($qx, $::ot_sp_cx0), $::ot_sp_cx1 - 20 * $u)}]; set qy [expr {min(max($qy, $::ot_sp_cy0), $::ot_sp_cy1 - 20 * $u)}]
    set cw0 $::ot_sp_cw
    foreach i $::ot_sp_icg_move {
      set ::ot_sp_cw [[$i getMaster] getWidth]; set ::ot_sp_retry 0
      lassign [ot_sp_legal $qx $qy] lx ly
      if {[dict exists $::ot_sp_rowor $ly]} { $i setOrient [dict get $::ot_sp_rowor $ly] }
      # Only the cells ON the port net (the ICG and its enable registers: their clock pins define the root) stay FIRM, and a
      # FIRM cell is dont_touch: the resizer sizes a FIRM cell in place and the legaliser cannot move it or a FIRM
      # neighbour (SM tile cluster eg r11 / wg r12: the cgi input buffer of the moved cone was sized up to BUFx12f by
      # repair_timing over the abutting FIRM AND3 -> DPL-0033 at 4_1_cts in both tiles).  The enable cone itself is left
      # movable (PLACED on the free sites found here), so any later sizing is legalised by detailed_placement.
      $i setLocation $lx $ly
      if {[lsearch -exact $::ot_sp_icg_port $i] >= 0} { $i setPlacementStatus FIRM; $i setDoNotTouch 1 } else { $i setPlacementStatus PLACED }
    }
    foreach i $::ot_sp_icg_move {
      if {[$i getPlacementStatus] in {FIRM LOCKED} && ![$i isDoNotTouch]} { error "OT_SPINE: moved cell [$i getName] is fixed but resizable" }
    }
    set ::ot_sp_cw $cw0
    lassign [[$::ot_sp_icg findITerm GCLK] getAvgXY] ok gx gy
    if {!$ok} { lassign [$::ot_sp_icg getLocation] gx gy }
    set ::ot_sp_root_xy [list $gx $gy]
    puts "OT_SPINE through ICG: [llength $::ot_sp_icg_move] cells moved beside the clock pin ([llength $::ot_sp_icg_port] port-net cells FIRM + dont_touch, enable cone movable)"
  }
  # sinks -> bins -> leaves
  set bins [dict create]; set ns 0
  foreach it [$net0 getITerms] {
    if {[$it getIoType] ne "INPUT"} continue
    lassign [$it getAvgXY] ok x y
    if {!$ok} { set l [[$it getInst] getLocation]; lassign $l x y }
    # OT_SPINE_MACRO_LEAF=1 (el1011-q-coll): a hard-macro clock pin is its own leaf, so a child-insertion target never
    # skews the flops that would otherwise share its bin
    if {[ot_sp_env OT_SPINE_MACRO_LEAF 0] eq "1" && [[[$it getInst] getMaster] isBlock]} {
      dict lappend bins "M[[$it getInst] getName]" [list $it $x $y]
    } else {
      dict lappend bins "[expr {int($x / $bin)}],[expr {int($y / $bin)}]" [list $it $x $y]
    }
    incr ns
  }
  set ::ot_sp_pos [dict create]; set ::ot_sp_cnt [dict create]; set ::ot_sp_members [dict create]; set nl 0
  set ::ot_sp_kids [dict create]; set lins [dict create]
  foreach k [dict keys $bins] {
    set lst [lsort -real -index 1 [dict get $bins $k]]
    for {set s 0} {$s < [llength $lst]} {incr s $lmax} {
      set grp [lrange $lst $s [expr {$s + $lmax - 1}]]
      set sx 0.0; set sy 0.0; set its {}
      foreach e $grp { lassign $e it x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; lappend its $it }
      set id "L[incr nl]"
      dict set ::ot_sp_pos $id [ot_sp_free [expr {int($sx / [llength $grp])}] [expr {int($sy / [llength $grp])}]]
      dict set ::ot_sp_cnt $id [llength $grp]
      dict set ::ot_sp_members $id $its
      # a leaf's own insertion = the largest child-insertion target among its sinks (kit dict, master -> ps)
      foreach v {::ot_ref_child_ins ::ot_sp_child_ins} {
        if {![info exists $v]} continue
        foreach it $its {
          set mn [[[$it getInst] getMaster] getName]
          if {[dict exists [set $v] $mn] && (![dict exists $lins $id] || [dict get [set $v] $mn] > [dict get $lins $id])} { dict set lins $id [dict get [set $v] $mn] }
        }
      }
    }
  }
  if {$nl == 0} { puts "OT_SPINE skipped: $port drives no sinks"; return 0 }
  set pb [$bt getBBox]
  set px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2}]
  if {$::ot_sp_root_xy ne ""} { lassign $::ot_sp_root_xy px py }
  if {[ot_sp_env OT_SPINE_SYM 0] eq "1"} {
    set root [ot_sp_sym_build [dict keys $::ot_sp_members] $lins [expr {min(max($px, $::ot_sp_cx0), $::ot_sp_cx1 - $::ot_sp_cw)}] [expr {min(max($py, $::ot_sp_cy0), $::ot_sp_cy1 - $::ot_sp_rh)}]]
  } else {
    set root [ot_sp_split [dict keys $::ot_sp_members]]
  }
  set ::ot_sp_leafnet [dict create]; set ::ot_sp_npad [dict create]
  foreach n [dict keys $::ot_sp_members] { dict set ::ot_sp_npad $n 0 }
  set treepad [expr {[ot_sp_env OT_SPINE_TREE_PAD 0] eq "1"}]
  if {$treepad} { foreach n [dict keys $::ot_sp_kids] { if {![dict exists $::ot_sp_npad $n]} { dict set ::ot_sp_npad $n 0 } } }
  ot_sp_emit $root $net0 [expr {min(max($px, $::ot_sp_cx0), $::ot_sp_cx1 - $::ot_sp_cw)}] [expr {min(max($py, $::ot_sp_cy0), $::ot_sp_cy1 - $::ot_sp_rh)}]
  set_propagated_clock [all_clocks]
  # equalise measured leaf arrivals with pad cells; the per-pad delay is learned from the previous round
  set iters [ot_sp_env OT_SPINE_ITERS 10]
  set stage [ot_sp_env OT_SPINE_STAGE_PS 60]
  set fstage [ot_sp_env OT_SPINE_FINE_PS 14]
  set tol [ot_sp_env OT_SPINE_TOL_PS 25]
  set prev ""; set padded [dict create]; set mode coarse
  set safe [expr {[ot_sp_env OT_SPINE_SAFE_BALANCE 0] eq "1"}]
  unset -nocomplain ::ot_sp_best_spread ::ot_sp_best_state
  for {set it 0} {$it <= $iters} {incr it} {
    set a [ot_sp_leaf_arrivals]
    set vals [dict values $a]
    set mx [tcl::mathfunc::max {*}$vals]; set mn [tcl::mathfunc::min {*}$vals]
    if {$prev ne "" && [dict size $padded]} {
      set g {}
      dict for {n c} $padded { lappend g [expr {([dict get $a $n] - [dict get $prev $n]) / double($c)}] }
      set g [lsort -real $g]; set m [lindex $g [expr {[llength $g] / 2}]]
      if {$m < 3.0} { set m 3.0 }
      if {$mode eq "coarse"} { set stage $m } else { set fstage $m }
    }
    puts [format "OT_SPINE iter %d (%s) leaves %d sinks %d cells %d leaf arrival %.1f..%.1f ps (spread %.1f) pad %.1f / %.1f ps" $it $mode $nl $ns $::ot_sp_nbuf $mn $mx [expr {$mx - $mn}] $stage $fstage]
    if {$safe && ![ot_sp_keep_best $a]} {
      set restored [ot_sp_leaf_arrivals]
      set rv [dict values $restored]
      set rsp [expr {[tcl::mathfunc::max {*}$rv] - [tcl::mathfunc::min {*}$rv]}]
      puts "OT_SPINE restored measured spread $rsp ps (best $::ot_sp_best_spread)"
      if {$rsp > $::ot_sp_best_spread + 1.0} { error "OT_SPINE best-checkpoint restore changed measured spread" }
      break
    }
    if {$it == $iters || $mx - $mn <= $tol} break
    if {$mode eq "coarse" && $mx - $mn < 1.6 * $stage} { set mode fine; set ::ot_sp_pm $::ot_sp_pmf }
    set st [expr {$mode eq "coarse" ? $stage : $fstage}]
    set prev $a; set padded [dict create]
    set need [dict create]
    dict for {n v} $a {
      set c [expr {int(floor(($mx - $v - 0.5 * $tol) / $st))}]
      # Small measured steps prevent a noisy fine-delay estimate from inserting
      # a long chain in one round.  Record the ACTUAL count for the next estimate.
      if {$safe} { set c [expr {min($c, $mode eq "fine" ? 1 : 3)}] }
      if {$c > 0} { dict set need $n $c; dict set padded $n $c }
    }
    if {$treepad} {
      # a leaf's pads are the sum along its root path = its need, so the per-pad delay estimate above is unchanged
      set np [ot_sp_tree_pad $root $need]
      puts "OT_SPINE tree pad: [dict size $need] early leaves served by $np pad cells"
    } else {
      dict for {n c} $need { ot_sp_pad $n $c }
    }
    if {[dict size $padded] == 0} break
  }
  foreach b $::ot_sp_insts { $b setDoNotTouch 1 }
  foreach n [concat [list $net0] [lmap b $::ot_sp_insts {[$b findITerm $::ot_sp_out] getNet}]] { $n setDoNotTouch 1 }
  ot_sp_check_legal
  set ::ot_sp_port $port
  puts "OT_SPINE done port $port buffers $::ot_sp_nbuf"
  return 1
}

# OT_SPINE_PORTS=ck,ckd builds each independent clock with the same measured
# balancing flow. A rest-only TritonCTS tree has no native boundary spread
# guarantee (qfd_coll_xfifo_native n13 CK:169 ps while CKD spine:29 ps).
# Each domain owns unique instance/net names; occupancy is rebuilt after each
# spine, so later domains preserve all earlier FIRM cell footprints.
# The ordinary one-port path retains its original cell names and topology.
proc ot_clock_spines {} {
  set ports [string map {, " "} [ot_sp_env OT_SPINE_PORTS ""]]
  set ::ot_sp_ports {}; set ::ot_sp_all_insts {}
  if {![llength $ports]} {
    if {![ot_clock_spine]} { return 0 }
    set ::ot_sp_ports [list $::ot_sp_port]
    set ::ot_sp_all_insts $::ot_sp_insts
    return 1
  }
  if {[llength [lsort -unique $ports]] != [llength $ports]} {
    error "OT_SPINE_PORTS: duplicate clock port"
  }
  set index 0
  foreach port $ports {
    if {![ot_clock_spine $port "clkbuf_sp_d[incr index]_"]} {
      error "OT_SPINE_PORTS: requested port $port has no clock sinks"
    }
    if {[lsearch -exact $::ot_sp_ports $::ot_sp_port] >= 0} {
      error "OT_SPINE_PORTS: two requested names resolve to $::ot_sp_port"
    }
    lappend ::ot_sp_ports $::ot_sp_port
    lappend ::ot_sp_all_insts {*}$::ot_sp_insts
  }
  return 1
}

if {[info procs clock_tree_synthesis] ne "" && [info procs ot_spine_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_spine_cts_orig
  proc clock_tree_synthesis {args} {
    if {[ot_sp_env OT_SPINE 1] eq "0"} { return [ot_spine_cts_orig {*}$args] }
    if {![ot_clock_spines]} { return [ot_spine_cts_orig {*}$args] }
    # the spine owns this port's whole clock network; TritonCTS runs only on request (other clock ports: OT_SPINE_CTS_REST=1)
    if {[ot_sp_env OT_SPINE_CTS_REST 0] eq "1"} {
      # el1014-root-macro-edge 2026-10-14 (qfd_coll_xfifo_native n13 gate): called without -clk_nets, TritonCTS finds
      # EVERY SDC clock again -- including the spine clock, whose 436 multi-sink spine nets it re-clusters and rebuffers
      # ('Clock net clkbuf_sp_N430_net has 2 sinks' ... ODB-0370 disconnect term A of dont_touch clkbuf_sp_N430).  The
      # rest pass must see only the OTHER clocks: -clk_nets = the source nets of every clock not rooted at the spine port.
      set rest [ot_sp_rest_nets]
      set i [lsearch -exact $args -clk_nets]
      if {$i >= 0} {
        set rest [lmap n [lindex $args [expr {$i + 1}]] { if {[lsearch -exact $::ot_sp_spine_nets $n] >= 0} continue; set n }]
        set args [lreplace $args $i [expr {$i + 1}]]
      }
      if {![llength $rest]} { puts "OT_SPINE rest: no other clock net, TritonCTS not run"; return }
      puts "OT_SPINE rest: TritonCTS on -clk_nets {$rest} (spine clock nets excluded)"
      return [ot_spine_cts_orig {*}$args -clk_nets [join $rest " "]]
    }
  }
}

# source nets of every SDC clock that is not the spine's (port / pin sources; the spine port's net and every net the
# spine drives are excluded).  Generated clocks are left to TritonCTS's own discovery through their master's net.
proc ot_sp_rest_nets {} {
  set blk [ord::get_db_block]
  set ::ot_sp_spine_nets [list]
  foreach port $::ot_sp_ports {
    set bt [$blk findBTerm $port]
    if {$bt ne "NULL" && $bt ne ""} { lappend ::ot_sp_spine_nets [[$bt getNet] getName] }
  }
  foreach b $::ot_sp_all_insts { set n [[$b findITerm $::ot_sp_out] getNet]; if {$n ne "NULL"} { lappend ::ot_sp_spine_nets [$n getName] } }
  set out {}
  foreach c [all_clocks] {
    if {[get_property $c is_generated]} continue
    foreach s [get_property $c sources] {
      set nm [get_full_name $s]
      set p [get_ports -quiet $nm]
      if {[llength $p]} {
        set b [$blk findBTerm [get_full_name $p]]
        if {$b eq "NULL" || $b eq ""} continue
        set n [$b getNet]
      } else {
        set it [$blk findITerm $nm]
        if {$it eq "NULL" || $it eq ""} continue
        set n [$it getNet]
      }
      if {$n eq "NULL" || $n eq ""} continue
      set nn [$n getName]
      if {[lsearch -exact $::ot_sp_spine_nets $nn] < 0 && [lsearch -exact $out $nn] < 0} { lappend out $nn }
    }
  }
  return $out
}
