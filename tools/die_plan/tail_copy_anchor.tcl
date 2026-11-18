# KV-HG-OPUS-SITE 11-18 (TAIL-COPY-SITE): site the landing-pad tail copies of bind's tail split (asbuilt.land_pad_tail_split,
# bind_pad_tail_split.py).  A split pad is a shared trunk ot_dp_dly D = pad - K plus one K-stage copy per consumer hard core
# (bind marks each copy `// landing pad tail copy for core <tag>`, gen_phys lists them in /work/tail_copies.tsv).  The split
# alone does nothing: GPL leaves the copy flops where it likes (QC st_a proof: worst copy -> pin wire 1585 ps, wns -901 ->
# -912).  Here, PRE_GLOBAL_PLACE (end of face_flops.tcl), like core_input_anchor.tcl's HB4 pad chains (r650/r660):
#   trunk end T  = L1 centre of every consumer pin of the copies that share one trunk (the point bind's K was sized from);
#   copy stage K = 1.5 um outside its core pin (its output BUF/INV cells with it), stages 1..K-1 at equal length on a Manhattan
#   route T -> pin that goes around the hard cores (L shape, else a Z through the channel beside a blocking core);
#   trunk last stage (the flop that feeds the copies) at T; earlier trunk stages are left to GPL (dly_spread anchors on T);
#   interior targets are pushed out of the macro boxes + 9 um halo, clamped into the core and snapped to a row/site.
# Every placed cell is FIRM through GPL and listed in ot_face_flops.txt, so face_flops_release.tcl releases it to PLACED for
# DPL.  A copy is sited only when its stages are intact (K flops in one chain, each stage feeding only the next, the last one
# reaching the pins of ONE hard macro): a copy Yosys folded into another (bind emits keep_hierarchy to prevent it) is
# reported as merged and left alone.  No tail_copies.tsv or no listed copy in the netlist = nothing happens.
# Pure helpers (tcs_*) are tested with tclsh (test_tail_copy_anchor.py).

# L1 (Manhattan) centre of points {{x y} ..}: minimises the largest Manhattan distance (u = x + y, v = x - y mid-ranges)
proc tcs_l1_centre {pts} {
  set u0 1e30; set u1 -1e30; set v0 1e30; set v1 -1e30
  foreach p $pts {
    lassign $p x y
    set u [expr {$x + $y}]; set v [expr {$x - $y}]
    if {$u < $u0} { set u0 $u }; if {$u > $u1} { set u1 $u }
    if {$v < $v0} { set v0 $v }; if {$v > $v1} { set v1 $v }
  }
  set u [expr {($u0 + $u1) / 2.0}]; set v [expr {($v0 + $v1) / 2.0}]
  return [list [expr {round(($u + $v) / 2.0)}] [expr {round(($u - $v) / 2.0)}]]
}
# push a point out of every box {x0 y0 x1 y1} it falls in: the nearest box edge (+ step) that lands in no other box, a few
# rounds when every edge of an abutted row lands in a neighbour; returns {x y clear}
proc tcs_inside {x y boxes} {
  foreach b $boxes { lassign $b x0 y0 x1 y1; if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} { return $b } }
  return ""
}
proc tcs_push_out {x y boxes step} {
  for {set round 0} {$round < 8} {incr round} {
    set b [tcs_inside $x $y $boxes]
    if {$b eq ""} { return [list $x $y 1] }
    lassign $b x0 y0 x1 y1
    set d [lsort -real -index 0 [list [list [expr {$x - $x0}] [expr {$x0 - $step}] $y] [list [expr {$x1 - $x}] [expr {$x1 + $step}] $y] \
                                      [list [expr {$y - $y0}] $x [expr {$y0 - $step}]] [list [expr {$y1 - $y}] $x [expr {$y1 + $step}]]]]
    set pick [lindex $d 0]
    foreach c $d { if {[tcs_inside [lindex $c 1] [lindex $c 2] $boxes] eq ""} { set pick $c; break } }
    lassign $pick _ x y
  }
  return [list $x $y [expr {[tcs_inside $x $y $boxes] eq ""}]]
}
# clamp into the core box and snap to the row/site grid (rows of one site, origin ox oy, site sw x sh)
proc tcs_snap {x y core ox oy sw sh} {
  lassign $core cx0 cy0 cx1 cy1
  set x [expr {max($cx0, min($cx1 - $sw, $x))}]; set y [expr {max($cy0, min($cy1 - $sh, $y))}]
  set x [expr {$ox + round(double($x - $ox) / $sw) * $sw}]; set y [expr {$oy + round(double($y - $oy) / $sh) * $sh}]
  if {$x > $cx1 - $sw} { set x [expr {$x - $sw}] }; if {$y > $cy1 - $sh} { set y [expr {$y - $sh}] }
  return [list $x $y]
}
# Manhattan route T -> L around the hard cores (kv3_pv_pair: OBS M1-M7, signal ceiling M7, so a hop cannot fly over a core).
# Candidates: the two L shapes, then Z shapes through a channel next to each core the L shapes hit (x = x0 - step / x1 + step,
# or y = y0 - step / y1 + step).  The shortest candidate that enters no core wins; if none is free, the one with the fewest
# entries.  Returns {length hits {x y} ...} (polyline incl. both ends).
proc tcs_seg_hits {a b boxes} {
  lassign $a ax ay; lassign $b bx by
  set n 0; set hit {}
  foreach bx_ $boxes {
    lassign $bx_ x0 y0 x1 y1
    if {$ay == $by} {
      if {$ay > $y0 && $ay < $y1 && max($ax, $bx) > $x0 && min($ax, $bx) < $x1} { incr n; lappend hit $bx_ }
    } elseif {$ax == $bx} {
      if {$ax > $x0 && $ax < $x1 && max($ay, $by) > $y0 && min($ay, $by) < $y1} { incr n; lappend hit $bx_ }
    }
  }
  return [list $n $hit]
}
proc tcs_path_hits {pts boxes} {
  set n 0; set hit {}
  for {set i 1} {$i < [llength $pts]} {incr i} {
    lassign [tcs_seg_hits [lindex $pts [expr {$i - 1}]] [lindex $pts $i] $boxes] m h
    incr n $m; foreach b $h { if {[lsearch -exact $hit $b] < 0} { lappend hit $b } }
  }
  return [list $n $hit]
}
proc tcs_path_len {pts} {
  set d 0
  for {set i 1} {$i < [llength $pts]} {incr i} { set d [expr {$d + [tcs_md [lindex $pts [expr {$i - 1}]] [lindex $pts $i]]}] }
  return $d
}
proc tcs_route {t l boxes step} {
  lassign $t tx ty; lassign $l lx ly
  set cands [list [list $t [list $lx $ty] $l] [list $t [list $tx $ly] $l]]
  set hit {}
  foreach c $cands { foreach b [lindex [tcs_path_hits $c $boxes] 1] { if {[lsearch -exact $hit $b] < 0} { lappend hit $b } } }
  foreach b $hit {
    lassign $b x0 y0 x1 y1
    foreach xc [list [expr {$x0 - $step}] [expr {$x1 + $step}]] { lappend cands [list $t [list $xc $ty] [list $xc $ly] $l] }
    foreach yc [list [expr {$y0 - $step}] [expr {$y1 + $step}]] { lappend cands [list $t [list $tx $yc] [list $lx $yc] $l] }
  }
  set best ""
  foreach c $cands {
    set n [lindex [tcs_path_hits $c $boxes] 0]; set len [tcs_path_len $c]
    if {$best eq "" || $n < [lindex $best 1] || ($n == [lindex $best 1] && $len < [lindex $best 0])} { set best [list $len $n {*}$c] }
  }
  return $best
}
# K stage targets at equal path length along a route {length hits pts..}: stage s at length * s / K (stage K = the end)
proc tcs_along {route k} {
  set len [lindex $route 0]; set pts [lrange $route 2 end]
  set out {}
  for {set s 1} {$s <= $k} {incr s} {
    set want [expr {double($len) * $s / $k}]; set acc 0.0
    for {set i 1} {$i < [llength $pts]} {incr i} {
      set a [lindex $pts [expr {$i - 1}]]; set b [lindex $pts $i]; set d [tcs_md $a $b]
      if {$acc + $d >= $want - 1e-6 || $i == [llength $pts] - 1} {
        set f [expr {$d > 0 ? min(1.0, ($want - $acc) / $d) : 1.0}]
        lappend out [list [expr {round([lindex $a 0] + ([lindex $b 0] - [lindex $a 0]) * $f)}] [expr {round([lindex $a 1] + ([lindex $b 1] - [lindex $a 1]) * $f)}]]
        break
      }
      set acc [expr {$acc + $d}]
    }
  }
  return $out
}
proc tcs_md {a b} { return [expr {abs([lindex $a 0] - [lindex $b 0]) + abs([lindex $a 1] - [lindex $b 1])}] }
# copy instance name of an odb cell name (`<path>.u_pdK_..._<pad>/<leaf>` kept, `<path>.u_pdK_..._<pad>.<leaf>` flat), or ""
proc tcs_copy_of {nm copies} {
  set nm [string map {\\ {}} $nm]
  if {![regexp {(?:^|[.])(u_pd[0-9]+_[A-Za-z0-9_]+)[./][^./]+$} $nm -> c]} { return "" }
  if {[dict exists $copies $c]} { return $c }
  return ""
}
# tail_copies.tsv rows `copy K group tag` -> dict copy -> {K group}
proc tcs_read_tsv {path} {
  set out [dict create]
  set fh [open $path r]
  foreach ln [split [read $fh] "\n"] {
    if {$ln eq "" || [string index $ln 0] eq "#"} continue
    lassign [split $ln "\t"] c k g
    dict set out $c [list $k $g]
  }
  close $fh
  return $out
}

proc tcs_isff {i} { return [regexp {^(DFF|SDF)} [[$i getMaster] getName]] }
proc tcs_isrep {i} { set m [$i getMaster]; return [expr {![$m isBlock] && [regexp {^(BUF|INV|HB)} [$m getName]]}] }
proc tcs_out {i} {
  foreach it [$i getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set n [$it getNet]; if {$n ne "" && $n ne "NULL"} { return $n } } }
  return ""
}
proc tcs_dnet {i} {
  foreach it [$i getITerms] { if {[[$it getMTerm] getName] eq "D"} { return [$it getNet] } }
  return ""
}
proc tcs_sinks {n} {
  set s {}
  foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "INPUT"} { lappend s $it } }
  return $s
}
# flop driving net n through unary BUF/INV/HB cells: {flop {rep cells}} or {}
proc tcs_ffdriver {n} {
  set reps {}
  for {set h 0} {$h < 6} {incr h} {
    if {$n eq "" || $n eq "NULL"} { return {} }
    set drv ""
    foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set drv [$it getInst] } }
    if {$drv eq ""} { return {} }
    if {[tcs_isff $drv]} { return [list $drv $reps] }
    if {![tcs_isrep $drv]} { return {} }
    lappend reps $drv
    set ins {}
    foreach it [$drv getITerms] { if {[[$it getMTerm] getIoType] eq "INPUT"} { set x [$it getNet]; if {$x ne "" && $x ne "NULL"} { lappend ins $x } } }
    if {[llength $ins] != 1} { return {} }
    set n [lindex $ins 0]
  }
  return {}
}
# from flop f, the unary BUF/INV/HB run its output takes: {rep cells} {sink iterms at the end}
proc tcs_follow {f} {
  set reps {}; set n [tcs_out $f]
  for {set h 0} {$h < 6} {incr h} {
    if {$n eq ""} { return [list $reps {}] }
    set s [tcs_sinks $n]
    if {[llength $s] != 1} { return [list $reps $s] }
    set c [[lindex $s 0] getInst]
    if {![tcs_isrep $c]} { return [list $reps $s] }
    lappend reps $c
    set n [tcs_out $c]
  }
  return [list $reps {}]
}
# pin box centre / point `dist` um outside the macro face nearest the pin (core_input_anchor nka_out_pos)
proc tcs_pin_xy {pin} { set b [$pin getBBox]; return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]] }
proc tcs_out_pos {pin dist_um dbu} {
  set mb [[$pin getInst] getBBox]; lassign [tcs_pin_xy $pin] px py
  set m [lsort -integer -index 0 [list [list [expr {$px - [$mb xMin]}] 0] [list [expr {[$mb xMax] - $px}] 1] \
                                  [list [expr {$py - [$mb yMin]}] 2] [list [expr {[$mb yMax] - $py}] 3]]]
  set g [expr {round($dist_um * $dbu)}]
  switch -- [lindex $m 0 1] {
    0 { return [list [expr {[$mb xMin] - $g}] $py] }
    1 { return [list [expr {[$mb xMax] + $g}] $py] }
    2 { return [list $px [expr {[$mb yMin] - $g}]] }
    default { return [list $px [expr {[$mb yMax] + $g}]] }
  }
}

proc tcs_run {} {
  if {![file exists /work/tail_copies.tsv]} { return }
  set copies [tcs_read_tsv /work/tail_copies.tsv]
  if {![dict size $copies]} { return }
  set blk [ord::get_db_block]
  set dbu [$blk getDbUnitsPerMicron]
  set hop_um [expr {[info exists ::env(OT_TAIL_SITE_HOP_UM)] ? $::env(OT_TAIL_SITE_HOP_UM) : 380.0}]
  set halo [expr {round(9.0 * $dbu)}]
  set cb [$blk getCoreArea]; set core [list [$cb xMin] [$cb yMin] [$cb xMax] [$cb yMax]]
  set row [lindex [$blk getRows] 0]
  lassign [$row getOrigin] ox oy
  set sw [[$row getSite] getWidth]; set sh [[$row getSite] getHeight]
  set boxes {}; set raw {}
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend raw [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]; lappend boxes [list [expr {[$b xMin] - $halo}] [expr {[$b yMin] - $halo}] [expr {[$b xMax] + $halo}] [expr {[$b yMax] + $halo}]] }
  }
  # flops of every listed copy (by name; the chain itself is checked by connectivity below)
  set cff [dict create]
  foreach i [$blk getInsts] {
    if {![tcs_isff $i]} continue
    set c [tcs_copy_of [$i getName] $copies]
    if {$c ne ""} { dict lappend cff $c $i }
  }
  # per copy: ordered stages, its core pin; per group: the pins of all its copies
  set ok [dict create]; set merged 0; set badout 0; set nocell 0
  set gpins [dict create]
  dict for {c kv} $copies {
    lassign $kv k g
    if {![dict exists $cff $c]} { incr nocell; continue }
    set ffs [dict get $cff $c]
    if {[llength $ffs] != $k} { incr merged; continue }
    # chain order: the first stage's D comes from outside the copy, stage s+1's D from stage s (through unary cells)
    set prev [dict create]; set first ""
    foreach f $ffs {
      set d [tcs_ffdriver [tcs_dnet $f]]
      set p [expr {[llength $d] ? [lindex $d 0] : ""}]
      if {$p ne "" && [lsearch -exact $ffs $p] >= 0} { dict set prev $p $f } else { set first $f }
    }
    if {$first eq "" || [dict size $prev] != $k - 1} { incr merged; continue }
    set chain [list $first]; set bad 0
    while {[dict exists $prev [lindex $chain end]]} {
      set f [lindex $chain end]
      lassign [tcs_follow $f] reps s
      if {[llength $s] != 1} { set bad 1; break }
      lappend chain [dict get $prev $f]
    }
    if {$bad || [llength $chain] != $k} { incr merged; continue }
    lassign [tcs_follow [lindex $chain end]] reps s
    set macs {}
    foreach it $s { set m [$it getInst]; if {![[$m getMaster] isBlock]} { set macs {}; break }; if {[lsearch -exact $macs $m] < 0} { lappend macs $m } }
    if {[llength $macs] != 1} { incr badout; continue }
    dict set ok $c [list $chain $s $g]
    foreach it $s { dict lappend gpins $g [tcs_pin_xy $it] }
  }
  set out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
  set ncopy 0; set ncell 0; set ntrunk 0; set maxhop 0; set over 0; set inside 0; set maxrhop 0; set rover 0; set crossing 0
  set tends [dict create]
  dict for {g pts} $gpins {
    lassign [tcs_l1_centre $pts] tx ty
    lassign [tcs_push_out $tx $ty $boxes $sw] tx ty clear
    if {!$clear} { incr inside }
    dict set tends $g [tcs_snap $tx $ty $core $ox $oy $sw $sh]
  }
  set tdone [dict create]
  dict for {c rec} $ok {
    lassign $rec chain s g
    set t [dict get $tends $g]
    # the pin nearest the trunk end; last stage 1.5 um outside it
    set pin ""; set best 1e30
    foreach it $s { set dd [tcs_md [tcs_pin_xy $it] $t]; if {$dd < $best} { set best $dd; set pin $it } }
    set l [tcs_out_pos $pin 1.5 $dbu]
    set k [llength $chain]
    set route [tcs_route $t $l $raw $halo]
    if {[lindex $route 1]} { incr crossing }
    set tg [tcs_along $route $k]
    set rh [expr {[lindex $route 0] / double($k) / $dbu}]
    if {$rh > $maxrhop} { set maxrhop $rh }; if {$rh > $hop_um} { incr rover }
    set pts {}
    for {set s_ 0} {$s_ < $k} {incr s_} {
      set f [lindex $chain $s_]
      if {$s_ == $k - 1} {
        set p $l
      } else {
        lassign [lindex $tg $s_] x y
        lassign [tcs_push_out $x $y $boxes $sw] x y clear
        if {!$clear} { incr inside }
        set p [tcs_snap $x $y $core $ox $oy $sw $sh]
      }
      lappend pts $p
      lassign [tcs_follow $f] reps _
      foreach cell [concat [list $f] $reps] {
        $cell setLocation {*}$p; $cell setPlacementStatus FIRM; puts $out [$cell getName]; incr ncell
      }
    }
    set q $t
    foreach p $pts { set h [expr {[tcs_md $q $p] / double($dbu)}]; if {$h > $maxhop} { set maxhop $h }; if {$h > $hop_um} { incr over }; set q $p }
    incr ncopy
    # trunk last stage: the flop that feeds this copy's first stage, when it is a trunk stage (u_pdN_..._t_<pad>) GPL owns
    if {![dict exists $tdone $g]} {
      dict set tdone $g 1
      set d [tcs_ffdriver [tcs_dnet [lindex $chain 0]]]
      if {[llength $d]} {
        lassign $d tf treps
        if {[regexp {(?:^|[.])u_pd[0-9]+_[A-Za-z0-9_]*_t_[0-9]+[./][^./]+$} [string map {\\ {}} [$tf getName]]] &&
            [$tf getPlacementStatus] ni {FIRM LOCKED COVER}} {
          foreach cell [concat [list $tf] $treps] {
            $cell setLocation {*}$t; $cell setPlacementStatus FIRM; puts $out [$cell getName]; incr ncell
          }
          incr ntrunk
        }
      }
    }
  }
  close $out
  puts [format "OT_TAIL_SITE copies %d of %d sited (%d cells, %d trunk ends, %d groups) merged %d no_cells %d bad_out %d max_hop %.1f um routed_hop %.1f um over_%g %d core_crossing %d in_halo %d (FIRM, released for DPL)" \
          $ncopy [dict size $copies] $ncell $ntrunk [dict size $gpins] $merged $nocell $badout $maxhop $maxrhop $hop_um $rover $crossing $inside]
}
tcs_run
