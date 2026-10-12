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
# FIRM + dont_touch, every spine net is CLOCK (clk_net_protect keeps resizer off it).  Leaves are then padded to equal
# MEASURED arrival (STA, placement parasitics), OT_SPINE_ITERS rounds.  TritonCTS is not run for this clock.
# Chain it FIRST in OT_CTS_FIX_HOOKS (it wraps clock_tree_synthesis; other hooks wrap it).  Knobs (env): OT_SPINE_PORT
# (default ck[0]), OT_SPINE_MACRO_LEAF 0, OT_SPINE_SEG 150, OT_SPINE_BIN 60, OT_SPINE_LEAF_N 8, OT_SPINE_HALO 3, OT_SPINE_CELL BUFx24_ASAP7_75t_R,
# OT_SPINE_ITERS 3.  Functional netlist unchanged (buffers only).

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

# snap to a legal row/site not used by another spine cell
proc ot_sp_legal {x y} {
  set sw $::ot_sp_sw; set rh $::ot_sp_rh; set w $::ot_sp_cw
  set ry [expr {$::ot_sp_ry0 + int(round(double($y - $::ot_sp_ry0) / $rh)) * $rh}]
  set sx [expr {$::ot_sp_rx0 + int(round(double($x - $::ot_sp_rx0) / $sw)) * $sw}]
  set nsite [expr {int(ceil(double($w) / $sw))}]
  if {![info exists ::ot_sp_cand]} {
    set c {}
    for {set k -40} {$k <= 40} {incr k} { for {set dr -10} {$dr <= 10} {incr dr} { lappend c [list [expr {abs($k) * 2 + abs($dr) * 3}] $k $dr] } }
    set ::ot_sp_cand [lsort -integer -index 0 $c]
  }
  foreach kc $::ot_sp_cand {
    lassign $kc _ k dr
    set cx [expr {$sx + $k * $nsite * $sw}]; set cy [expr {$ry + $dr * $rh}]
    if {[ot_sp_blocked $cx $cy [expr {$cx + $w}] [expr {$cy + $rh}]]} continue
    set ok 1
    for {set s -1} {$s <= $nsite} {incr s} { if {[dict exists $::ot_sp_used "$cy,[expr {$cx + $s * $sw}]"]} { set ok 0; break } }
    if {!$ok} continue
    for {set s 0} {$s < $nsite} {incr s} { dict set ::ot_sp_used "$cy,[expr {$cx + $s * $sw}]" 1 }
    return [list $cx $cy]
  }
  # crowded: move the target 10 um outward and retry
  if {[incr ::ot_sp_retry] < 40} {
    lassign [ot_sp_free [expr {$x + 10 * $::ot_sp_dbu}] $y] fx fy
    set r [ot_sp_legal $fx $fy]; set ::ot_sp_retry 0; return $r
  }
  error "OT_SPINE: no legal site near $x $y"
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

# build node n's buffer fed by innet from (px,py); recurse
proc ot_sp_emit {n innet px py} {
  lassign [dict get $::ot_sp_pos $n] nx ny
  lassign [ot_sp_path $px $py $nx $ny] pts len
  set net $innet; set k 0
  foreach p $pts { lassign [ot_sp_buf "clkbuf_sp_${n}_r[incr k]" {*}$p $net] net }
  lassign [ot_sp_buf "clkbuf_sp_${n}" $nx $ny $net] onet lx ly
  if {[dict exists $::ot_sp_kids $n]} {
    foreach c [dict get $::ot_sp_kids $n] { ot_sp_emit $c $onet $lx $ly }
  } else {
    dict set ::ot_sp_leafnet $n $onet
    foreach it [dict get $::ot_sp_members $n] { $it disconnect; $it connect $onet }
  }
}

# insert `count` pad buffers in front of leaf n's buffer (between its driver net and its A pin)
proc ot_sp_pad {n count} {
  set lb [$::ot_sp_blk findInst "clkbuf_sp_${n}"]
  set ait [$lb findITerm $::ot_sp_in]
  set net [$ait getNet]
  set loc [$lb getLocation]; lassign $loc lx ly
  $ait disconnect
  set p [dict get $::ot_sp_npad $n]
  for {set i 0} {$i < $count} {incr i} {
    lassign [ot_sp_buf "clkbuf_sp_${n}_p[incr p]" $lx $ly $net $::ot_sp_pm] net
  }
  dict set ::ot_sp_npad $n $p
  $ait connect $net
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

proc ot_clock_spine {} {
  set ::ot_sp_blk [ord::get_db_block]
  set blk $::ot_sp_blk
  set ::ot_sp_dbu [$blk getDbUnitsPerMicron]
  set u $::ot_sp_dbu
  set port [ot_sp_env OT_SPINE_PORT {ck[0]}]
  set bt [$blk findBTerm $port]
  if {$bt eq "NULL" || $bt eq ""} { puts "OT_SPINE skipped: no port $port"; return 0 }
  set net0 [$bt getNet]
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
  set ::ot_sp_rowor [dict create]; set ::ot_sp_ry0 ""; set ::ot_sp_rx0 ""
  foreach r [$blk getRows] {
    lassign [$r getOrigin] ox oy
    if {$::ot_sp_ry0 eq "" || $oy < $::ot_sp_ry0} { set ::ot_sp_ry0 $oy }
    if {$::ot_sp_rx0 eq "" || $ox < $::ot_sp_rx0} { set ::ot_sp_rx0 $ox }
    dict set ::ot_sp_rowor $oy [$r getOrient]
    set ::ot_sp_sw [[$r getSite] getWidth]; set ::ot_sp_rh [[$r getSite] getHeight]
  }
  set ::ot_sp_used [dict create]; set ::ot_sp_nbuf 0; set ::ot_sp_nn 0; set ::ot_sp_insts {}
  # existing fixed / firm standard cells (tapcells, pin cells) keep their sites
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} continue
    if {[lsearch -exact {FIRM LOCKED FIXED COVER} [$i getPlacementStatus]] < 0} continue
    set b [$i getBBox]
    for {set x [$b xMin]} {$x < [$b xMax]} {incr x $::ot_sp_sw} { dict set ::ot_sp_used "[$b yMin],$x" 1 }
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
    }
  }
  if {$nl == 0} { puts "OT_SPINE skipped: $port drives no sinks"; return 0 }
  set root [ot_sp_split [dict keys $::ot_sp_members]]
  set pb [$bt getBBox]
  set px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2}]
  set ::ot_sp_leafnet [dict create]; set ::ot_sp_npad [dict create]
  foreach n [dict keys $::ot_sp_members] { dict set ::ot_sp_npad $n 0 }
  ot_sp_emit $root $net0 [expr {min(max($px, $::ot_sp_cx0), $::ot_sp_cx1 - $::ot_sp_cw)}] [expr {min(max($py, $::ot_sp_cy0), $::ot_sp_cy1 - $::ot_sp_rh)}]
  set_propagated_clock [all_clocks]
  # equalise measured leaf arrivals with pad cells; the per-pad delay is learned from the previous round
  set iters [ot_sp_env OT_SPINE_ITERS 10]
  set stage [ot_sp_env OT_SPINE_STAGE_PS 60]
  set fstage [ot_sp_env OT_SPINE_FINE_PS 14]
  set tol [ot_sp_env OT_SPINE_TOL_PS 25]
  set prev ""; set padded [dict create]; set mode coarse
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
    if {$it == $iters || $mx - $mn <= $tol} break
    if {$mode eq "coarse" && $mx - $mn < 1.6 * $stage} { set mode fine; set ::ot_sp_pm $::ot_sp_pmf }
    set st [expr {$mode eq "coarse" ? $stage : $fstage}]
    set prev $a; set padded [dict create]
    dict for {n v} $a {
      set c [expr {int(floor(($mx - $v - 0.5 * $tol) / $st))}]
      if {$c > 0} { ot_sp_pad $n $c; dict set padded $n $c }
    }
    if {[dict size $padded] == 0} break
  }
  foreach b $::ot_sp_insts { $b setDoNotTouch 1 }
  foreach n [concat [list $net0] [lmap b $::ot_sp_insts {[$b findITerm $::ot_sp_out] getNet}]] { $n setDoNotTouch 1 }
  puts "OT_SPINE done port $port buffers $::ot_sp_nbuf"
  return 1
}

if {[info procs clock_tree_synthesis] ne "" && [info procs ot_spine_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_spine_cts_orig
  proc clock_tree_synthesis {args} {
    if {[ot_sp_env OT_SPINE 1] eq "0"} { return [ot_spine_cts_orig {*}$args] }
    if {![ot_clock_spine]} { return [ot_spine_cts_orig {*}$args] }
    # the spine owns this port's whole clock network; TritonCTS runs only on request (other clock ports: OT_SPINE_CTS_REST=1)
    if {[ot_sp_env OT_SPINE_CTS_REST 0] eq "1"} { return [ot_spine_cts_orig {*}$args] }
  }
}
