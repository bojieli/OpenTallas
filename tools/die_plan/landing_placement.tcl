# Generated caller provides cland_groups: {prefix rect tag}, and
# cland_status: {net x y}. Called after existing face/reset/FT FIRM sites.
if {![info exists ff_blk] || ![info exists ff_dbu]} { error "OT_CLAND missing face placement context" }
set cland_occ {}; set cland_done {}; set cland_n 0
proc cland_ours {name} { return [regexp {(^|[/.])u_cland_} $name] }
# Ring/collector placement changes cell locations/status only. Start a fresh
# instance epoch on every source (clock/reset synthesis may have changed the DB
# before the hook); preserve original DB iteration order within each group.
unset -nocomplain cland_instance_index
proc cland_group_insts {prefix} {
 global ff_blk cland_instance_index
 if {![regexp {^[A-Za-z_][A-Za-z0-9_]*$} $prefix]} {
  set hit {}
  foreach i [$ff_blk getInsts] {
   if {[regexp [format {(^|[/.])%s[/.]} $prefix] [$i getName]]} {lappend hit $i}
  }
  return $hit
 }
 if {![info exists cland_instance_index]} {
  set cland_instance_index {}
  foreach i [$ff_blk getInsts] {
   # The final path component is the cell itself: the legacy regex requires
   # a separator after the group name, so that component is not a group.
   set groups [lrange [split [string map {. /} [$i getName]] /] 0 end-1]
   foreach group [lsort -unique $groups] {dict lappend cland_instance_index $group $i}
  }
 }
 if {[dict exists $cland_instance_index $prefix]} {return [dict get $cland_instance_index $prefix]}
 return {}
}
proc cland_occupy {x y w h} {
 global cland_occ ff_y0 ff_rh
 set r0 [expr {int(floor(double($y-$ff_y0)/$ff_rh))}]
 set r1 [expr {int(ceil(double($y+$h-$ff_y0)/$ff_rh))}]
 # Store the occupied union, rather than every historical reservation.  Dense
 # row packing creates adjacent ranges; keeping each one made first-fit scans
 # quadratic.  Merging only overlapping/touching ranges preserves every gap and
 # the final first-fit location (a scan cannot stop inside an occupied chain).
 for {set r $r0} {$r<$r1} {incr r} {
  set ranges {}
  if {[dict exists $cland_occ $r]} {set ranges [dict get $cland_occ $r]}
  lappend ranges [list $x [expr {$x+$w}]]
  set merged {}
  foreach range [lsort -real -index 0 $ranges] {
   lassign $range l u
   if {![llength $merged] || $l>[lindex $merged end 1]} {
    lappend merged [list $l $u]
   } else {
    lassign [lindex $merged end] ml mu
    lset merged end [list $ml [expr {max($mu,$u)}]]
   }
  }
  dict set cland_occ $r $merged
 }
}
foreach i [$ff_blk getInsts] {
 if {[cland_ours [$i getName]]} continue
 if {[$i getPlacementStatus] ni {FIRM LOCKED} && ![[$i getMaster] isBlock]} continue
 set b [$i getBBox]
 cland_occupy [$b xMin] [$b yMin] [expr {[$b xMax]-[$b xMin]}] [expr {[$b yMax]-[$b yMin]}]
}
# KW6-CLASS 11-04 (S81 ot_s81sl_leaf__t34/t66 3_5 DPL-0033 "Placed in rows check failed", diamond 0 failures): the row
# model ff_orient is per y only, so the row-cut halo around a macro (rows stop 2 um beside it, core 215.1 in a row ending
# 214.11) was free space and FIRM ring/collector cells landed outside any row.  The x gaps of each row y are occupied.
proc cland_occupy_row_gaps {rows} {
 global ff_x0 ff_x1 ff_rh
 set spans {}
 foreach r $rows { set b [$r getBBox]; dict lappend spans [$b yMin] [list [$b xMin] [$b xMax]] }
 dict for {y row_spans} $spans {
  set at $ff_x0
  foreach s [lsort -integer -index 0 $row_spans] {
   lassign $s l u
   if {$l > $at} { cland_occupy $at $y [expr {$l-$at}] $ff_rh }
   set at [expr {max($at,$u)}]
  }
  if {$at < $ff_x1} { cland_occupy $at $y [expr {$ff_x1-$at}] $ff_rh }
 }
}
cland_occupy_row_gaps [$ff_blk getRows]
# Opt-in (gen_phys reserved_sites_um): die clock-tree reservations are occupied space for ring/status cells.
if {[info exists ::cland_avoid_rects]} {
 foreach r $::cland_avoid_rects { lassign $r ra rb rc rd; cland_occupy $ra $rb [expr {$rc-$ra}] [expr {$rd-$rb}] }
}
# DIE-KV-42 10-29 (KV-022 SD try3 3_5 DPL-0033): a ring band that overlaps a HARD placement blockage (pdn.tcl PHY
# supply region, die clock islands, reserved clock sites) packs ring cells where detailed placement cannot keep them;
# fail closed here, before any cell is placed. Bands clear of every hard blockage are unchanged. The die clock-tree
# reserved sites (::cland_avoid_rects, occupied above) stay legal inside a band: the ring is packed around them.
set cland_hard {}
set cland_avoid_db {}
if {[info exists ::cland_avoid_rects]} { foreach r $::cland_avoid_rects { lappend cland_avoid_db [lmap v $r {expr {int($v)}}] } }
# DIE-KV-64 11-03 (KV kv3_hgi_v5/v6/v7 "band overlaps hard placement blockage"): the die clock driver islands
# (die_islands.tcl, global ::di_rects in DBU, one 2.7 x 0.81 um driver site each) are reserved clock sites like
# ::cland_avoid_rects: occupied space the ring is packed around, not a band/blockage conflict.
if {[info exists ::di_rects]} {
 foreach r $::di_rects {
  set r [lmap v $r {expr {int($v)}}]
  if {$r in $cland_avoid_db} continue
  lappend cland_avoid_db $r
  lassign $r ra rb rc rd; cland_occupy $ra $rb [expr {$rc-$ra}] [expr {$rd-$rb}]
 }
}
foreach bk [$ff_blk getBlockages] {
 if {[$bk isSoft]} continue
 set bb [$bk getBBox]; set hr [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
 if {$hr in $cland_avoid_db} continue
 lappend cland_hard $hr
 # DPL treats hard blockages as unavailable row sites even when getRows
 # still returns a full-width row. Every cland_put caller and capacity bound
 # must share this occupancy, including non-ring structural helper groups.
 lassign $hr hx0 hy0 hx1 hy1
 cland_occupy $hx0 $hy0 [expr {$hx1-$hx0}] [expr {$hy1-$hy0}]
}
foreach spec $cland_groups {
 lassign $spec prefix rect tag
 if {![string match {ring:*} $tag]} continue
 lassign $rect ax ay bx by
 set ax [expr {int(ceil($ax*$ff_dbu))}];set ay [expr {int(ceil($ay*$ff_dbu))}]
 set bx [expr {int(floor($bx*$ff_dbu))}];set by [expr {int(floor($by*$ff_dbu))}]
 foreach hb $cland_hard {
  lassign $hb hx0 hy0 hx1 hy1
  if {min($bx,$hx1) > max($ax,$hx0) && min($by,$hy1) > max($ay,$hy0)} {
   error "OT_CLAND band $prefix ($tag) {$rect} overlaps hard placement blockage {[expr {$hx0/double($ff_dbu)}] [expr {$hy0/double($ff_dbu)}] [expr {$hx1/double($ff_dbu)}] [expr {$hy1/double($ff_dbu)}]}"
  }
 }
}
# DIE-S81-47 11-01 (S81 "landing band absent", 17 bands in 11 svc/leaf types): a band with plan rects_um (2..N
# disjoint rects, each within reach of its bus pin) is emitted as one cland_groups entry per rect, same prefix and ring
# tag, nearest the pin first.  The ring is packed into the rects in that order (cland_put moves to the next rect when
# one is full); plans whose ring tags each appear once (every band with a single rect_um) are unchanged.
set cland_multi {}
foreach spec $cland_groups {
 lassign $spec prefix rect tag
 if {[string match {ring:*} $tag]} { dict lappend cland_multi $tag $rect }
}
foreach k [dict keys $cland_multi] { if {[llength [dict get $cland_multi $k]] < 2} { dict unset cland_multi $k } }
set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
# FLOW-6 10-30: widest master of a cell's drive family (OT_CLAND_FIT_RESERVE=resize), cached per master name.
set cland_famw {}
proc cland_family_w {m} {
 global cland_famw
 set nm [$m getName];set w [$m getWidth];set h [$m getHeight]
 if {[dict exists $cland_famw $nm]} { return [dict get $cland_famw $nm] }
 set fw $w
 if {[regexp {^(.*x)p?[0-9]+[a-z]*(_.*)$} $nm -> pre suf]} {
  foreach lib [[ord::get_db] getLibs] {
   foreach mm [$lib getMasters] {
    if {[regexp {^(.*x)p?[0-9]+[a-z]*(_.*)$} [$mm getName] -> p2 s2] && $p2 eq $pre && $s2 eq $suf
        && [$mm getHeight] == $h && [$mm getWidth] > $fw} { set fw [$mm getWidth] }
   }
  }
 }
 dict set cland_famw $nm $fw
 return $fw
}
# Explicit per-band +x opt-in: bit-major flops fill upward within a column,
# then advance across x. Density spacing is vertical; drive-family width is
# still reserved horizontally so in-place resizing cannot overlap a neighbor.
proc cland_put_column {i ax ay bx by tag sp cur fw} {
 global ff_x0 ff_y0 ff_rh ff_sw ff_dbu ff_orient cland_occ cland_done cland_n cland_fh cland_col_cursor cland_col_reduce cland_col_dry
 set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
 set rw [expr {int(ceil(double(max($w,$fw))/$ff_sw))*$ff_sw}]
 set rh [expr {int(ceil(double($h)/0.4*$sp/$ff_rh))*$ff_rh}]
 # Column density spacing is a row quantum. Capacity selection may remove
 # whole padding rows, never the physical cell height or horizontal reserve.
 if {[info exists cland_col_reduce]} {
  set rh [expr {max(int(ceil(double($h)/$ff_rh))*$ff_rh,$rh-$cland_col_reduce*$ff_rh)}]
 }
 set x0 [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set y0 [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 set x $x0;set y $y0;set cw 0
 if {$cur && [info exists cland_col_cursor] && [llength $cland_col_cursor]==3} {
  lassign $cland_col_cursor x y cw
 }
 while {$x+$rw<=$bx} {
  for {} {$y+$h<=$by} {incr y $ff_rh} {
   if {![dict exists $ff_orient $y]} continue
   set free 1
   set r0 [expr {int(($y-$ff_y0)/$ff_rh)}]
   set r1 [expr {int(ceil(double($y+$rh-$ff_y0)/$ff_rh))}]
   for {set r $r0} {$r<$r1} {incr r} {
    if {![dict exists $cland_occ $r]} continue
    foreach interval [dict get $cland_occ $r] {
     lassign $interval l u
     if {$x<$u && $x+$rw>$l} {set free 0;break}
    }
    if {!$free} break
   }
   if {!$free} continue
   set dry [expr {[info exists cland_col_dry] && $cland_col_dry}]
   if {!$dry} {
    if {[$i getPlacementStatus] eq "FIRM"} {$i setPlacementStatus PLACED}
    $i setOrient [dict get $ff_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
   }
   cland_occupy $x $y $rw $rh
   if {$cur} {set cland_col_cursor [list $x [expr {$y+$rh}] [expr {max($cw,$rw)}]]}
   dict set cland_done [$i getName] 1;incr cland_n
   if {!$dry} {
   puts $cland_fh "[$i getName]\tcland:$tag\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\t-"
   }
   return 1
  }
  set x [expr {$x+max($cw,$rw)}];set y $y0;set cw 0
 }
 return 0
}
# DIE-HEAD-13 opt-in: sp = reserve spread given by the caller (else from the tag), cur = resume the row scan at the last
# site this band placed (ordered fill: O(n) instead of the O(n^2) rescan from the band corner). Defaults unchanged.
proc cland_put {i rect tag {sp {}} {cur 0}} {
 global ff_x0 ff_y0 ff_x1 ff_y1 ff_rh ff_sw ff_dbu ff_orient cland_occ cland_done cland_n cland_fh cland_cursor
 # multi-rect band (::cland_multi, called with its first rect): a cell with no site in the current rect goes to the
 # next rect (the row cursors restart there); the rect index stays where the last cell went.  Any other error, and a
 # cell that fits in no rect, fails closed.  Single-rect bands skip this block.
 if {([info exists ::cland_multi] && [dict exists $::cland_multi $tag]) && ![info exists ::cland_multi_in]
     && [lmap v $rect {expr {double($v)}}] eq [lmap v [lindex [dict get $::cland_multi $tag] 0] {expr {double($v)}}]} {
  set rects [dict get $::cland_multi $tag]
  set k 0; if {[info exists ::cland_multi_at] && [dict exists $::cland_multi_at $tag]} { set k [dict get $::cland_multi_at $tag] }
  for {} {$k < [llength $rects]} {incr k} {
   set ::cland_multi_in 1
   set rc [catch {cland_put $i [lindex $rects $k] $tag $sp $cur} err opts]
   unset ::cland_multi_in
   if {!$rc} {
    if {![info exists ::cland_fill_dry] && !([info exists ::cland_multi_at] && [dict exists $::cland_multi_at $tag] && [dict get $::cland_multi_at $tag] == $k)} {
     puts "OT_CLAND multi-rect $tag: rect [expr {$k+1}]/[llength $rects] {[lindex $rects $k]} from [$i getName]"
    }
    dict set ::cland_multi_at $tag $k
    return
   }
   if {![string match {OT_CLAND no legal*} $err]} { return -options $opts $err }
   set cland_cursor {}; set ::cland_col_cursor {}
  }
  error "OT_CLAND no legal nonoverlapping row/site in reserved band for [$i getName] ($tag, [llength $rects] rects)"
 }
 set name [$i getName]
 if {[dict exists $cland_done $name]} { error "OT_CLAND duplicate placement $name" }
 lassign $rect ax ay bx by
 set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
 # Evaluate the existing half-window slide eligibility before conservative DBU quantization.
 # QC coll_ftn: face 691.2 / core edge 686.88 / half-window 2.16 is exactly eligible,
 # but ceil(689.040... * 1000) became 689041 and incorrectly rejected the window.
 # The drawn bounds remain ceil/floor-conservative; this only removes the rounding artefact.
 set sxov [expr {min($bx,double($ff_x1)/$ff_dbu)-max($ax,double($ff_x0)/$ff_dbu)}]
 set syov [expr {min($by,double($ff_y1)/$ff_dbu)-max($ay,double($ff_y0)/$ff_dbu)}]
 set slide_x [expr {2.0*$sxov+1e-9 >= $ax-$bx}]
 set slide_y [expr {2.0*$syov+1e-9 >= $ay-$by}]
 set ax [expr {int(ceil($ax*$ff_dbu))}];set ay [expr {int(ceil($ay*$ff_dbu))}]
 set bx [expr {int(floor($bx*$ff_dbu))}];set by [expr {int(floor($by*$ff_dbu))}]
 # FLOW-GEN-1 10-28 (DIE-HEAD-9 bug 5): a window centred within half its size of the core edge (a status pin in the
 # core margin) clips to less than the cell; slide it, same size, inside the core (windows that fit are unchanged,
 # windows farther out still fail closed)
 set ov [expr {min($bx,$ff_x1)-max($ax,$ff_x0)}]
 if {$ov < $w && $bx-$ax >= $w && $slide_x} {
  if {$ax < $ff_x0} { set bx [expr {$bx+$ff_x0-$ax}];set ax $ff_x0 } elseif {$bx > $ff_x1} { set ax [expr {$ax-($bx-$ff_x1)}];set bx $ff_x1 }
 }
 set ov [expr {min($by,$ff_y1)-max($ay,$ff_y0)}]
 if {$ov < $h && $by-$ay >= $h && $slide_y} {
  if {$ay < $ff_y0} { set by [expr {$by+$ff_y0-$ay}];set ay $ff_y0 } elseif {$by > $ff_y1} { set ay [expr {$ay-($by-$ff_y1)}];set by $ff_y1 }
 }
 # DIE-KV-33 opt-in OT_CLAND_FIT_RESERVE=1: the site must be free of other occupancy over the whole reserved footprint
 # (rw, as cland_occupy reserves it), not just the body, so an in-place upsize by timing-driven GPL (FIRM cells are
 # resized, not moved) cannot grow into a tapcell / foreign FIRM cell (KV io_ft kits_gen5 3_5 DPL-0033: 3 FIRM
 # INVx1 -> INVx3 over TAPCELLs). Default (unset) unchanged.
 set fw $w
 # DIE-S81-53/BAND 11-04 (S81 leaf t4/t6 ft5_i, t71 ft3_i, 1-bit buses: 82 flops, need 60 um2, band 411-425 um2): the fill
 # spread of a +ff ring is max(1, 0.9*band/need), 6.4 here, so one 1.08 um flop asked for 17.28 um free in a 15.14 um band,
 # and a tapcell beside the band (t4 y >= 32.4, x 1026.16) took every row with 26 flops left.  That footprint is a fill
 # target, not upsize room: the fit footprint of a +ff ring stays at the base w/0.4.  The reservation (rw) is unchanged.
 if {[info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "1"} {
  set fsp $sp; if {$fsp eq {}} { set fsp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> fsp }
  if {$fsp > 1.0 && [string match {ring:*+ff*} $tag]} { set fsp 1.0 }
  set fw [expr {max($w,int(ceil(double($w)/0.4*$fsp/$ff_sw))*$ff_sw)}]
 }
 # FLOW-6 10-30 opt-in OT_CLAND_FIT_RESERVE=resize: the site must be free of other occupancy over the widest drive
 # variant of the cell's own family (same name stem/suffix and height, e.g. DFFHQNx1 -> DFFHQNx3), not the w/0.4*spread
 # reserve of "=1": timing-driven GPL resizes FIRM cells in place (HEAD n3_turn v3nofr 3_5 DPL-0033: FIRM ring
 # DFFHQNx1 abutting a TAPCELL resized to DFFHQNx2, +54 dbu over it) and the "=1" reserve overfills ring bands
 # (HEAD st_m v3). Default (unset) and "=1" unchanged.
 if {([info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "resize") || [info exists ::cland_pinslot_fit]} { set fw [cland_family_w $m] }
 # FLOW-6 10-30 (HEAD n3_turn / turn_a v3 status d1_o/t_o): a status window centred in the core margin can overlap the
 # core by more than one cell height and still hold ONE row only (pin y 602.144, window 599.984..604.304, core top
 # 600.48 -> row 600.21); when that row has no fitting site, the window (same size) slides inside the core and is
 # scanned once more. A window placed on the first scan is unchanged; a window that is not slide-eligible, already
 # inside the core, or still without a site fails closed as before.
 set cland_win [list $ax $ay $bx $by]
 foreach cland_pass {0 1} {
 if {$cland_pass} {
  lassign $cland_win ax ay bx by
  set moved 0
  if {$slide_x && $bx-$ax <= $ff_x1-$ff_x0} {
   if {$ax < $ff_x0} { set bx [expr {$bx+$ff_x0-$ax}];set ax $ff_x0;set moved 1 } elseif {$bx > $ff_x1} { set ax [expr {$ax-($bx-$ff_x1)}];set bx $ff_x1;set moved 1 }
  }
  if {$slide_y && $by-$ay <= $ff_y1-$ff_y0} {
   if {$ay < $ff_y0} { set by [expr {$by+$ff_y0-$ay}];set ay $ff_y0;set moved 1 } elseif {$by > $ff_y1} { set ay [expr {$ay-($by-$ff_y1)}];set by $ff_y1;set moved 1 }
  }
  if {!$moved} break
 }
 set ax [expr {max($ff_x0,$ax)}];set ay [expr {max($ff_y0,$ay)}]
 set bx [expr {min($ff_x1,$bx)}];set by [expr {min($ff_y1,$by)}]
 set startx [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set starty [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 if {[string match {ring:*+x+ff*} $tag]} {
  if {$sp eq {}} {error "OT_CLAND column fill requires explicit FF spread"}
  if {[cland_put_column $i $ax $ay $bx $by $tag $sp $cur $fw]} {return}
  continue
 }
 # AUTOBUILD-PIPE-4 10-31 (GEOM-87, HEAD l47 hd_st_m/hd_st_str/hd_st_turn E-face pin_reg 55-128 um): ::cland_xdesc (set
 # by cland_place_pinslot for a band whose pins lie beyond its E edge) scans each row from the band's HIGH-x (pin-side)
 # edge leftwards and mirrors the spacing reserve to the cell's interior side; the row order and fail-closed error are
 # unchanged, the resume cursor is not used.  Unset = the left-to-right scan below, byte-identical.
 if {[info exists ::cland_xdesc] && $::cland_xdesc} {
  set endx [expr {$ff_x0+int(floor(double($bx-$w-$ff_x0)/$ff_sw))*$ff_sw}]
  for {set y $starty} {$y+$h<=$by} {incr y $ff_rh} {
   if {![dict exists $ff_orient $y]} continue
   set x $endx
   while {$x>=$startx && $x>=$ax} {
    set lim $x;set r0 [expr {int(($y-$ff_y0)/$ff_rh)}];set r1 [expr {int(ceil(double($y+$h-$ff_y0)/$ff_rh))}]
    for {set r $r0} {$r<$r1} {incr r} {
     if {![dict exists $cland_occ $r]} continue
     foreach interval [dict get $cland_occ $r] {
      lassign $interval l u
      if {$x<$u && $x+$fw>$l} { set lim [expr {min($lim,$l-$fw)}] }
     }
    }
    if {$lim<$x} { set x [expr {$ff_x0+int(floor(double($lim-$ff_x0)/$ff_sw))*$ff_sw}];continue }
    set dry [info exists ::cland_fill_dry]
    if {!$dry} {
    if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED }
    $i setOrient [dict get $ff_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
    }
    if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }
    set rw [expr {int(ceil(double($w)/0.4*$sp/$ff_sw))*$ff_sw}]
    cland_occupy [expr {$x+$w-$rw}] $y $rw $h
    dict set cland_done $name 1;incr cland_n
    if {!$dry} { puts $cland_fh "$name\tcland:$tag\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\t-" }
    return
   }
  }
  continue
 }
 if {!$cland_pass && $cur && [llength $cland_cursor]==2} { lassign $cland_cursor cy cx; if {$cy>$starty} { set starty $cy } } else { set cy {} }
 for {set y $starty} {$y+$h<=$by} {incr y $ff_rh} {
  if {![dict exists $ff_orient $y]} continue
  set x $startx
  if {$cur && $cy ne {} && $y==$cy && $cx>$x} { set x $cx }
  while {$x+$w<=$bx} {
   set skip $x;set r0 [expr {int(($y-$ff_y0)/$ff_rh)}];set r1 [expr {int(ceil(double($y+$h-$ff_y0)/$ff_rh))}]
   for {set r $r0} {$r<$r1} {incr r} {
    if {![dict exists $cland_occ $r]} continue
    foreach interval [dict get $cland_occ $r] {
     lassign $interval l u
     if {$x<$u && $x+$fw>$l} { set skip [expr {max($skip,$u)}] }
    }
   }
   if {$skip>$x} { set x [expr {$ff_x0+int(ceil(double($skip-$ff_x0)/$ff_sw))*$ff_sw}];continue }
   set dry [info exists ::cland_fill_dry]
   if {!$dry} {
   if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED }
   $i setOrient [dict get $ff_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
   }
   # Reserve spacing as well as the real body. Density margin permits the
   # datapath mux/control cells and leaves room for clock/reset repair.
   # DIE-HEAD-12 opt-in band spread: tag ring:<bus>@<spread> widens the reserved footprint so the ring fills its band
   if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }
   # The resize-family fit must remain occupied for subsequent cells too.
   # LEP TXI INVx1 (162 DBU) reserved 432 DBU, then grew in place to
   # INVx8 (540 DBU), overlapping the next FIRM cell by 108 DBU.
   set rw [expr {int(ceil(max(double($w)/0.4*$sp,$fw)/$ff_sw))*$ff_sw}]
   cland_occupy $x $y $rw $h
   if {$cur} { set cland_cursor [list $y [expr {$x+$rw}]] }
   dict set cland_done $name 1;incr cland_n
   if {!$dry} { puts $cland_fh "$name\tcland:$tag\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\t-" }
   return
  }
 }
 }
 error "OT_CLAND no legal nonoverlapping row/site in reserved band for $name ($tag)"
}
proc cland_drivers {n} {
 set d {}
 foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { lappend d [$it getInst] } }
 return $d
}
# AUTOBUILD-PIPE-2 10-31 (collectors) + KIT-TRIAGE-1/G4 11-01 (status): a cell with no free site in its +-2.16 um window
# takes the window grown about the same centre x2, x4, x8, x16, x32 (<= +-69.12 um); still none fails closed with the
# same error.  QC slw_hc1 11-05: collector point inside ring band rs_n0, x8 had no site.  KV kv3_io_cor@4 (3_3 'no legal ... (status:landing_ready_ft10_i)'): the ready/fault status stages of a ring
# share ONE plan point on the S face, inside the FIRM pin-register strip of the neighbouring bus bits, so the 4.32 um
# window had no site; a registered status output 17 um from its pin is far inside any timing / reach budget.
proc cland_put_grow {i rect tag kind} {
 lassign $rect ax ay bx by
 set cx [expr {($ax+$bx)/2.0}]; set cy [expr {($ay+$by)/2.0}]; set hx [expr {($bx-$ax)/2.0}]; set hy [expr {($by-$ay)/2.0}]
 foreach g {1 2 4 8 16 32} {
  set w [list [expr {$cx-$hx*$g}] [expr {$cy-$hy*$g}] [expr {$cx+$hx*$g}] [expr {$cy+$hy*$g}]]
  if {![catch {cland_put $i $w $tag} err]} {
   if {$g > 1} { puts "OT_CLAND $kind grow [$i getName] ($tag): window x$g (+-[format %.2f [expr {$hx*$g}]] um)" }
   return
  }
  if {![string match {OT_CLAND no legal*} $err]} { error $err $::errorInfo }
 }
 error $err
}
# DIE-QC-97 11-09 (QC slw_stm_v1__cl05fc43f7__cl2086fa2c a11, first band fail on a kit generated with 0b305f2395):
# the writer-start window 445.85..450.17 x 634.22..638.54 had rows and no macro or blockage, but face_flops.tcl had
# placed FIRM ft-station flops (u_ft_x_fw_fe_p1_o_2/q[*]) over all of it before the landing groups; plan-time windows
# cannot see station sites.  A reader/writer START relay whose window centre lies inside the core and has no site
# takes the same grow as status, collector and local-reset cells (cland_put_grow: x2..x32 about the same centre, same
# fail-closed error).  A window centred outside the core takes the plain path (slide or fail closed) unchanged.
# Windows on a hard macro were moved out at plan time (landing_place.py, 0b305f2395) before this runs.
# OT_CLAND_START_GROW=0 restores the plain path for every START window.
proc cland_put_start {i rect tag} {
 global ff_x0 ff_y0 ff_x1 ff_y1 ff_dbu
 lassign $rect ax ay bx by
 set x [expr {($ax+$bx)/2.0*$ff_dbu}]; set y [expr {($ay+$by)/2.0*$ff_dbu}]
 if {!([info exists ::env(OT_CLAND_START_GROW)] && $::env(OT_CLAND_START_GROW) eq "0") &&
     $x > $ff_x0 && $x < $ff_x1 && $y > $ff_y0 && $y < $ff_y1} {
  cland_put_grow $i $rect $tag start
 } else { cland_put $i $rect $tag }
}
# S81-TYPES-4 11-07 (S81 leaf macro-facing batch: t7 t10 t56 t67 place FAIL, relay window inside a moved macro, deeper
# than the x32 window reaches; t10 rst_rl_148 is 73.8 um inside u_vsw): OT_MACRO_MOVES edits macro_place.tcl only, so the
# plan's relay xy stands inside the moved macro (the relay flop itself is legalized out later; its pre-DPL site is still
# under the macro, so following it does not help: t56 pilot).  On kits holding macro_moves.json a collector with no site
# about its plan xy takes the same window law just outside the nearest edge of the macro that covers that xy, nearest
# edge first.  A window that fits, or an xy under no macro: unchanged.  Still no site: fails closed.
# DIE-S81-85 11-09 CLAND-RESET-IN-MACRO (S81 kw43 ot_s81sl_leaf__t33 / t43 3_3 'OT_CLAND no legal nonoverlapping row/site in
# reserved band for u_bound.u_cland_reset_rst_rl_189/_1_ (raw-copy-optional)', rst_rl_99 on t43): the TYPE-SAFE-5 leaf
# ctap+moves plan event folded the macro moves into hard_cores (no macro_moves.json) and left the reset tree relay xy
# where it was, 107 / 73 um inside u_lf.u_vsw; the reset raw copy shares the collector window and is placed FIRST (the
# optional loop runs before the collector loop), by plain grow, with no macro exit.  The macro exit no longer needs
# macro_moves.json (the DB macro boxes ARE the sites this kit places around) and raw copies take it too (kind raw-copy).
# Only a cell that has no site even at x32 reaches it, so every kit that places today is unchanged; gen
# (landing_place._collector_window) moves such windows already, this is the run-time net for kits whose windows were
# drawn against other macro sites.
proc cland_macro_exits {cx cy hx hy} {
 set out {}
 foreach m [$::ff_blk getInsts] {
  if {![[$m getMaster] isBlock]} continue
  set b [$m getBBox]
  set x0 [expr {[$b xMin]/double($::ff_dbu)}]; set y0 [expr {[$b yMin]/double($::ff_dbu)}]
  set x1 [expr {[$b xMax]/double($::ff_dbu)}]; set y1 [expr {[$b yMax]/double($::ff_dbu)}]
  if {$cx <= $x0 || $cx >= $x1 || $cy <= $y0 || $cy >= $y1} continue
  set g [expr {2.0*max($hx,$hy)}]
  foreach {d nx ny} [list [expr {$cx-$x0}] [expr {$x0-$g}] $cy [expr {$x1-$cx}] [expr {$x1+$g}] $cy \
                          [expr {$cy-$y0}] $cx [expr {$y0-$g}] [expr {$y1-$cy}] $cx [expr {$y1+$g}]] {
   lappend out [list $d $nx $ny [$m getName]]
  }
 }
 return [lsort -real -index 0 $out]
}
proc cland_put_collector {i rect tag {kind collector}} {
 if {![catch {cland_put_grow $i $rect $tag $kind} err opts]} { return }
 if {![string match {OT_CLAND no legal*} $err]} { return -options $opts $err }
 lassign $rect ax ay bx by
 set cx [expr {($ax+$bx)/2.0}]; set cy [expr {($ay+$by)/2.0}]; set hx [expr {($bx-$ax)/2.0}]; set hy [expr {($by-$ay)/2.0}]
 foreach e [cland_macro_exits $cx $cy $hx $hy] {
  lassign $e d nx ny mn
  if {![catch {cland_put_grow $i [list [expr {$nx-$hx}] [expr {$ny-$hy}] [expr {$nx+$hx}] [expr {$ny+$hy}]] $tag $kind} err2 opts2]} {
   puts "OT_CLAND $kind exits macro [$i getName] ($tag): plan xy [format {%.2f %.2f} $cx $cy] under $mn, window at [format {%.2f %.2f} $nx $ny] ([format %.2f $d] um to the edge)"
   return
  }
  if {![string match {OT_CLAND no legal*} $err2]} { return -options $opts2 $err2 }
 }
 return -options $opts $err
}
# Registered status outputs sit at their declared source point, separately
# from the ring storage band; the collector then follows its original tree.
# Status placement only moves cells; it does not create, remove or rename nets.
# Reset the lookup epoch on every hook invocation (reset/clock hooks may have
# changed connectivity before this source). Cache simple suffixes in one DB
# pass instead of scanning every net for every parent-prefixed status output.
proc cland_status_net {net} {
 global ff_blk cland_status_suffix
 set n [$ff_blk findNet $net]
 if {$n ne "NULL"} { return $n }
 set candidates {}
 if {![regexp {[/.]} $net]} {
  if {![info exists cland_status_suffix]} {
   set cland_status_suffix {}
   foreach dn [$ff_blk getNets] {
    set name [$dn getName]
    if {[regexp {^.*[/.]([^/.]+)$} $name -> tail]} {
     dict lappend cland_status_suffix $tail $dn
    }
   }
  }
  if {[dict exists $cland_status_suffix $net]} {set candidates [dict get $cland_status_suffix $net]}
 } else {
  # Unusual hierarchical requested names retain the original exact suffix law.
  set length [string length $net]
  foreach dn [$ff_blk getNets] {
   set name [$dn getName]
   if {[string length $name] > $length && [string range $name end-[expr {$length-1}] end] eq $net
       && [string index $name end-$length] in {. /}} {lappend candidates $dn}
  }
 }
 if {[llength $candidates] == 1} {return [lindex $candidates 0]}
 if {[llength $candidates] > 1} {
  error "OT_CLAND ambiguous status net $net: [llength $candidates] hierarchical matches"
 }
 return NULL
}
unset -nocomplain cland_status_suffix
foreach spec $cland_status {
 lassign $spec net x y
 set n [cland_status_net $net]
 if {$n eq "NULL"} { error "OT_CLAND missing actual status net $net" }
 set drivers [cland_drivers $n]
 # FLOW-GEN-1 10-28 (DIE-HEAD-9 bug 4): ASAP7 maps the status FF as DFFHQN + INV (no Q flop): follow exactly one
 # inverter to its single QN flop driver; the flop is placed at the status point, the INV is left to GPL beside it
 if {[llength $drivers]==1 && [string match "INV*" [[[lindex $drivers 0] getMaster] getName]]} {
  set cland_inv [lindex $drivers 0];set cland_qd {}
  foreach it [$cland_inv getITerms] {
   if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} { set cland_qd [cland_drivers [$it getNet]] }
  }
  if {[llength $cland_qd]==1 && [string match "*DFF*" [[[lindex $cland_qd 0] getMaster] getName]]} { set drivers $cland_qd }
 }
 # DIE-QC-83 11-06 (QC HC0 AP parent 3_3 'OT_CLAND landing_ready_rsf_i requires one actual dedicated output FF'): a
 # landing ring hardened as a hard child (QC hc0/sul1 ring-split events) drives its ready/fault status from inside the
 # macro.  The status FF lives in the signed child and the plan places the macro, so there is no parent cell to place.
 # Only a single block driver is skipped; any other non-FF driver still fails closed below.
 if {[llength $drivers]==1 && [[[lindex $drivers 0] getMaster] isBlock]} {
  puts "OT_CLAND status $net: driver [[lindex $drivers 0] getName] is hard child [[[lindex $drivers 0] getMaster] getName] (status FF inside the child), not placed"
  continue
 }
 if {[llength $drivers]!=1 || ![string match "*DFF*" [[[lindex $drivers 0] getMaster] getName]]} {
  error "OT_CLAND $net requires one actual dedicated output FF"
 }
 set cland_sw [list [expr {$x-2.16}] [expr {$y-2.16}] [expr {$x+2.16}] [expr {$y+2.16}]]
 # grow a window whose largest grown size (+-17.28 um) touches the core (a crowded window); a status point farther out
 # fails closed.  DIE-S81-53/BAND 11-04 (S81 leaf t56 landing_ready_ft9_i): a pin at y 0 with the core at y 4.32 has a
 # +-2.16 um window clear of the core, so it took the plain path: slid into the core, inside the FIRM ft9 pin-register
 # diamond (columns 2.16 um apart, y 4.3-24), with no site and no grow; free sites were 12 um away.
 if {($x+17.28)*$ff_dbu > $ff_x0 && ($x-17.28)*$ff_dbu < $ff_x1 &&
     ($y+17.28)*$ff_dbu > $ff_y0 && ($y-17.28)*$ff_dbu < $ff_y1} {
  cland_put_grow [lindex $drivers 0] $cland_sw status:$net status
 } else { cland_put [lindex $drivers 0] $cland_sw status:$net }
}
foreach spec $cland_optional_groups {
 lassign $spec prefix rect tag
 foreach i [cland_group_insts $prefix] {
  set nm [$i getName]
  if {[dict exists $cland_done $nm]} continue
  # DIE-QC-73 11-05 (QC su_c, su_l1): a single reset copy whose 4.32 um window lies in a ring band the FIRM fill took
  # had no site and stopped global placement; same grow as status and collector cells, same fail-closed error.
  # DIE-S81-85 11-09: and the same macro exit as its collector (cland_put_collector kind raw-copy).
  cland_put_collector $i $rect $tag raw-copy
 }
}
# DIE-HEAD-13 10-28 opt-in ring_place=ff (tag suffix +ff, compose(band_ring="ff")): only the ring's SEQUENTIAL cells are
# placed FIRM, in bit-major order (a 2-D register x[slot][bit] sorts by bit, then slot, so the DEPTH copies of one bit and
# their write/read logic sit together), at the spread that fills the band to cland_ff_fill; the ring's combinational logic
# (write enables, read muxes, count compare) is left to global placement next to the flops it connects. Measured why
# (DIE-HEAD-12 probe B, hd_tile): ring FIRM in netlist order 676,805 GRT overflow, flops-only FIRM -97 %.
set cland_ff_fill 0.90
set cland_cursor {}
# DIE-HEAD-32 10-29: rev=1 (tag +ffr, an lsb_high bus) sorts the bit index DESCENDING (slots stay ascending), so the
# band, filled from its low corner, holds the highest bit where the lsb_high pins put it; rev=0 is byte-identical.
proc cland_ffkey {nm {rev 0} {wch 0} {nbits 0} {wwc 0} {rwc 0} {tail_groups 0}} {
 if {[regexp {^([^\[]*)\[([0-9]+)\\?\]\\?\[([0-9]+)\\?\](.*)$} $nm -> b s i t]} {
  if {$rev} { set i [expr {999999999-$i}] }
  return [format {%s|%09d|%09d|%s} [string trimright $b \\] $i $s $t]
 }
 # FLOW-10 10-30 (HEAD st_str / wshim_rx r2r 510): the read-side registers of a chunked ring (ot_meso_dsel per 64-bit
 # chunk: dch[c].u_dsel/y[i] = word bit c*WCH+i, dch[c].u_dsel/di[k] = the chunk's one-hot selects) have no adjacent
 # [slot][bit] index, so they keyed by raw name and all packed BEFORE the storage at the band's low corner (st_str: 517
 # y regs in y 27..64 while their bits span y 25..231 -> ring-to-station-0 hop 510 um).  With the ring's chunk width
 # (wch > 0, from cland_place_ff) each y register takes its word bit's storage key, right after that bit's slots; the
 # di selects sit at their chunk centre.  wch 0 (no chunked dsel registers in the band) = the old raw-name key.  Word bits
 # at or above nbits (the band bus's port width, when known) are the ring's own status/tag bits: they keep the raw-name
 # key (band low corner, where the plan sites the status stages), as before.
 if {$wch > 0 && [regexp {^(.*[/.])dch\\?\[([0-9]+)\\?\]\.u_dsel/(y|di)\\?\[([0-9]+)\\?\](.*)$} $nm -> b c kind i t]} {
  if {$kind eq "y"} {
   set bit [expr {$c*$wch+$i}]; set s 999999998
  } else {
   set bit [expr {$c*$wch+$wch/2}]; set s [expr {999999990+$i}]
   # Optional bounded read chunks keep their selector at the payload group.
   # The last chunk may contain fewer data bits plus constant/status tails.
   if {$tail_groups && $rwc > 0} {
    set s [expr {999999970+$i}]
    if {$nbits > 0 && $c*$wch < $nbits} { set bit [expr {min($bit,$nbits-1)}] }
   }
  }
  if {$nbits > 0 && $bit >= $nbits} { return $nm }
  if {$rev} { set bit [expr {999999999-$bit}] }
  return [format {%s|%09d|%09d|%s} "${b}s_d" $bit $s $t]
 }
 # KV-PLAN-2 11-09 (KV kv3_hgi_v3 ft27_i, GRT-0116 30448 gcells): synthesis may name a chunked ring's STORAGE flops by
 # the chunk wire, dch[c].sd_c[k] (ot_dp_clk_landing_ca: sd_c[slot*WCH+i] = s_d[slot][c*WCH+i]), not s_d[slot][bit].
 # Those names missed the [slot][bit] key, so the START control rekey moved ALL storage (4,436 of 5,493 ring flops) to
 # one block after the START bit while each read register sat at its own bit: every bit's storage-to-read net crossed
 # the band (3,315 ring nets cut the pocket centre).  Key each one as storage slot k/WCH of word bit c*WCH+k%WCH, the
 # same key s_d[slot][bit] gets.  Bits at or above nbits keep the raw-name key, as for y; wch 0 is unchanged.
 if {$wch > 0 && [regexp {^(.*[/.])dch\\?\[([0-9]+)\\?\]\.sd_c\\?\[([0-9]+)\\?\](.*)$} $nm -> b c k t]} {
  set bit [expr {$c*$wch+$k%$wch}]
  if {$nbits <= 0 || $bit < $nbits} {
   if {$rev} { set bit [expr {999999999-$bit}] }
   return [format {%s|%09d|%09d|%s} "${b}s_d" $bit [expr {$k/$wch}] $t]
  }
 }
 # Opt-in local-WREG form: each kept writer enable follows its own payload
 # group; replicated read-select flops follow their own read group. Their key
 # slot is below the legacy control-rekey range, so START packing cannot undo it.
 if {$wwc > 0 && [regexp {^(.*[/.])g_wreg\.sl\\?\[([0-9]+)\\?\]\.ch\\?\[([0-9]+)\\?\]\.u_wen/(.*)$} $nm -> b sl c tail]} {
  set bit [expr {$c*$wwc+$wwc/2}]
  if {$tail_groups && $nbits > 0 && $c*$wwc < $nbits} { set bit [expr {min($bit,$nbits-1)}] }
  if {$nbits <= 0 || $bit < $nbits} {
   if {$rev} { set bit [expr {999999999-$bit}] }
   return [format {%s|%09d|%09d|%s} "${b}s_d" $bit [expr {999999980+$sl}] $tail]
  }
 }
 if {$rwc > 0 && $wch > 0 && [regexp {^(.*[/.])dch\\?\[([0-9]+)\\?\]\.u_dsel/g_srep\.sr\\?\[([0-9]+)\\?\]\.u_sel/di\\?\[([0-9]+)\\?\](.*)$} $nm -> b c r sl tail]} {
  set bit [expr {$c*$wch+$r*$rwc+$rwc/2}]
  if {$nbits <= 0 || $bit < $nbits} {
   if {$rev} { set bit [expr {999999999-$bit}] }
   return [format {%s|%09d|%09d|%s} "${b}s_d" $bit [expr {999999970+$sl}] $tail]
  }
 }
 return $nm
}
# chunk width WCH of a band's chunked ring read registers (max y index + 1; every chunk has WCH bits), 0 when none
proc cland_kbit {kf rev} { scan $kf %d v; return [expr {$rev ? 999999999-$v : $v}] }
# DIE-HEAD-43 c3 (FLOW-11 shared): bus bit (index) whose pin centre is nearest the START pin {x y}; bxy = {{bit x y} ..}
proc cland_nearest_bit {sx bxy} {
 lassign $sx px py; set best {}; set bd 0
 foreach e $bxy { lassign $e bi cx cy; set d [expr {abs($cx-$px)+abs($cy-$py)}]; if {$best eq {} || $d < $bd} { set best $bi; set bd $d } }
 return [list $best $bd]
}
# ring CONTROL registers (raw-name keys = not storage/read bits) and status/s_tag keys (bits >= bus width, other storage
# base, or the 99999999x tag slots) move right after bus bit kb; returns {n_moved ffs}
proc cland_ctl_rekey {ffs base kb nbb rev} {
 set nc 0
 set out [lmap pr $ffs {
  set k [lindex $pr 0]
  set f [split $k |]
  if {$k eq [lindex $f 0]} {
   incr nc; list [format {%s|%09d|%09d|%s} $base $kb 999999997 $k] [lindex $pr 1]
  } elseif {[llength $f] >= 3 && ([lindex $f 0] ne $base || [cland_kbit [lindex $f 1] $rev] >= $nbb || ([scan [lindex $f 2] %d] >= 999999990 && [scan [lindex $f 2] %d] < 999999998))} {
   incr nc; list [format {%s|%09d|%09d|%s} $base $kb 999999996 $k] [lindex $pr 1]
  } else { set pr }
 }]
 return [list $nc $out]
}
# FREG-1 (DIE-HEAD-60 11-04, hd_turn_a GRT-0183): a registered face's g_freg.u_face/q[N] has no [slot][bit] index, so
# cland_ctl_rekey took all 566 as control registers and packed them at the START-pin bit: y 820..880 against pins
# 700..1010, median pin-to-flop 104 um, max 196 um, one net boxed in.  q[N] registers bus bit N: key it first in that bit,
# on the pin side.  N at or above the bus width (status / start bits) stays control.
proc cland_freg_rekey {ffs base nbb rev} {
 set nf 0
 set out [lmap pr $ffs {
  set k [lindex $pr 0]
  if {$k eq [lindex [split $k |] 0] && [regexp {g_freg\.u_face/q\\?\[([0-9]+)\\?\]} $k -> b] && $b < $nbb} {
   incr nf; list [format {%s|%09d|%09d|!freg} $base [expr {$rev ? 999999999-$b : $b}] 0] [lindex $pr 1]
  } else { set pr }
 }]
 return [list $nf $out]
}
proc cland_dsel_wch {names} {
 set w 0
 foreach nm $names {
  if {[regexp {[/.]dch\\?\[[0-9]+\\?\]\.u_dsel/y\\?\[([0-9]+)\\?\]} $nm -> i]} { set w [expr {max($w,$i+1)}] }
 }
 return $w
}
# DIE-S81-66/CLS 11-05 (KW-RELAUNCH-1 class CLAND-BAND; S81 dsdv_slice_c1x_C__t3 attempt 3, ring sid_i0: ~66 flops in a
# 25.9 x 15.9 um band, fill spread ~6.4, failed at its 63rd flop with the band ~85 % empty): the old fill reserves each
# flop rw = w/0.4 x sp along its row (DIE-S81-53 keeps only the FIT footprint at w/0.4, the reservation stays rw), so in
# a row whose free run is shorter than two reservations (here an obstacle took x 1399.7..1410.5 of a 1399.7..1425.6 band
# in every row from y 550.8) one flop fits per row and the ring runs out of ROWS, not area.  Dry-run the whole ordered
# fill at sp (no DB move, no record); if it does not fit, shrink the spread in 3/4 steps down to 1.0 and place at the
# first spread at which the whole ring fits.  A ring that fits at sp keeps sp (placement unchanged); a ring that fits at
# no spread keeps sp and fails closed exactly as before.  OT_CLAND_SPREAD_FIT=0 turns the dry run off (old behaviour).
proc cland_fill_spread {ordered rect tag sp} {
 global cland_occ cland_done cland_n cland_cursor
 if {[info exists ::env(OT_CLAND_SPREAD_FIT)] && $::env(OT_CLAND_SPREAD_FIT) eq "0"} { return $sp }
 set had_at [info exists ::cland_multi_at]
 set saved [list $cland_occ $cland_done $cland_n $cland_cursor [expr {$had_at ? $::cland_multi_at : {}}]]
 set tsp $sp
 try {
  set ::cland_fill_dry 1
  while 1 {
   lassign $saved cland_occ cland_done cland_n cland_cursor
   if {$had_at} { set ::cland_multi_at [lindex $saved 4] } else { unset -nocomplain ::cland_multi_at }
   set rc [catch { foreach pr $ordered {cland_put [lindex $pr 1] $rect $tag $tsp 1} } msg opts]
   if {!$rc} { break }
   if {![string match {OT_CLAND no legal*} $msg]} { return -options $opts $msg }
   if {$tsp <= 1.0} { set tsp $sp; break }
   set tsp [expr {max(1.0,$tsp*0.75)}]
  }
 } finally {
  unset -nocomplain ::cland_fill_dry
  lassign $saved cland_occ cland_done cland_n cland_cursor
  if {$had_at} { set ::cland_multi_at [lindex $saved 4] } else { unset -nocomplain ::cland_multi_at }
 }
 if {$tsp != $sp} { puts "OT_CLAND fill spread $tag: [llength $ordered] flops do not fit at spread [format %.4f $sp] (row-limited), placed at [format %.4f $tsp]" }
 return $tsp
}
# Select the largest native-row spacing that fits the WHOLE ordered band.
# The continuous 90% area estimate can overflow after vertical ceil rounding
# (HEAD turn_b: 2885 cells fit, then writer bit12 fails). Probe the exact same
# scanner/foreign occupancy/width policy transactionally before moving cells.
proc cland_column_select {ffs rect tag sp} {
 global ff_rh cland_occ cland_done cland_n cland_cursor cland_col_cursor cland_col_reduce cland_col_dry
 set saved [list $cland_occ $cland_done $cland_n $cland_cursor $cland_col_cursor]
 set maxrows 0
 foreach pr $ffs {
  set h [[[lindex $pr 1] getMaster] getHeight]
  set maxrows [expr {max($maxrows,int(ceil(double($h)/0.4*$sp/$ff_rh)))}]
 }
 try {
  set cland_col_dry 1
  for {set r 0} {$r <= $maxrows} {incr r} {
   lassign $saved cland_occ cland_done cland_n cland_cursor cland_col_cursor
   set cland_col_reduce $r
   set rc [catch {
    foreach pr $ffs {cland_put [lindex $pr 1] $rect $tag $sp 1}
   } msg opts]
   if {!$rc} {return $r}
   if {![string match {OT_CLAND no legal nonoverlapping row/site in reserved band*} $msg]} {
    return -options $opts $msg
   }
  }
  # A physically full band still fails, without partial placement or records.
  return -options $opts $msg
 } finally {
  lassign $saved cland_occ cland_done cland_n cland_cursor cland_col_cursor
  unset -nocomplain cland_col_reduce cland_col_dry
 }
}
# FLOW-11 10-30 (DIE-HEAD-43 (C), GEOM-68 band-form class: HEAD turn_a/turn_b/st_str/wshim_rx pin_reg_p90 65-92):
# opt-in OT_CLAND_PINSLOT=1 (plan budgets.cland_pinslot_types) places each bus bit's ring slot flops next to that bit's
# own pin instead of packing the band bit-major from its low corner (turn_a t_i: 566 bits x 4 slots packed in y
# 708..973 while the pins span 709..1008 -> bit 0 slots 35 um below its pin; farthest-slot p90 69 um).  Each flop is
# kept in key order and stretched over the pin span (cland_place_pinslot).  Ring flops without a bus-bit key keep the old
# cursor fill after them.  Unset = byte-identical placement.
# bit -> {x y} (dbu) centres of the bus pins <bus>[bit]
proc cland_bus_pins {bus} {
 global ff_blk
 set out {}
 foreach bt [$ff_blk getBTerms] {
  if {[regexp {^(.*)\[([0-9]+)\]$} [$bt getName] -> bn bi] && $bn eq $bus} {
   set bb [$bt getBBox]
   dict set out $bi [list [expr {([$bb xMin]+[$bb xMax])/2}] [expr {([$bb yMin]+[$bb yMax])/2}]]
  }
 }
 return $out
}
# Ring flops with a bus-bit key keep their key (bit-major) order and are stretched over the span of their pins: flop j
# of n starts the band cursor at the row of lo + (hi-lo)*j/(n-1) (lo/hi = pin y of the first/last flop's bit), so each
# bit's flops sit next to its pin row, never before it, and rows are filled left to right as before.  Aiming each flop
# at its own pin with a nearest-free-site search drifts instead (HEAD turn_a what-if: the band's last bits found their
# rows taken and fell back to holes 323 um away).  Applies to a pin column whose y order follows the key order (the
# plan's +ff/+ffr choice); any other band (pins along x, or y order against the keys) keeps the old fill.
proc cland_place_pinslot {ordered rect tag sp pins rev {psp 1.0}} {
 global ff_dbu ff_y0 ff_rh cland_cursor
 lassign $rect ax ay bx by
 set rest {}; set al {}
 foreach pr $ordered {
  set k [lindex $pr 0]
  if {![regexp {^[^|]+\|([0-9]+)\|} $k -> kf] || ![dict exists $pins [set bit [cland_kbit $kf $rev]]]} { lappend rest $pr; continue }
  lappend al [list [lindex $pr 1] [dict get $pins $bit]]
 }
 set n [llength $al]; set cland_cursor {}
 if {$n} {
  set xs [lmap e $al {lindex $e 1 0}]; set ys [lmap e $al {lindex $e 1 1}]
  set lo [lindex $ys 0]; set hi [lindex $ys end]
  set dy [expr {[tcl::mathfunc::max {*}$ys]-[tcl::mathfunc::min {*}$ys]}]
  set dx [expr {[tcl::mathfunc::max {*}$xs]-[tcl::mathfunc::min {*}$xs]}]
 }
 if {!$n || $hi <= $lo || $dy < $dx} {
  set sp [cland_fill_spread $ordered $rect $tag $sp]
  foreach pr $ordered {cland_put [lindex $pr 1] $rect $tag $sp 1}
  return [list 0 [llength $ordered] "pins not a y column in key order: old fill"]
 }
 # the stretched rows sit at the plan spread, tighter than the fill spread: fit each flop on its widest drive variant
 # (as OT_CLAND_FIT_RESERVE=resize) so the in-place GPL upsize cannot grow over a tapcell (turn_a what-if without it:
 # 3_5 DPL-0033, 55 ring DFFHQNx1 -> x2 over TAPCELLs)
 # AUTOBUILD-PIPE-4 10-31 (GEOM-87): pins beyond the band's E edge -> fill each row from the band's E (pin-side) edge
 # (cland_put ::cland_xdesc); W-face bands already fill from their pin side (the low-x edge)
 set xdesc [expr {[tcl::mathfunc::min {*}$xs] >= int(floor($bx*$ff_dbu))}]
 set ::cland_pinslot_fit 1
 if {$xdesc} { set ::cland_xdesc 1 }
 try {
 set j 0
 foreach e $al {
  set i [lindex $e 0]
  set ty [expr {$lo+($hi-$lo)*double($j)/($n-1)}]; incr j
  set ry [expr {$ff_y0+int(round(($ty-$ff_rh/2.0-$ff_y0)/$ff_rh))*$ff_rh}]
  set w [list $ax [expr {max($ay,double($ry)/$ff_dbu)}] $bx $by]
  # target row to band top all taken: the whole band, first fit (fails closed with the usual error)
  if {[catch {cland_put $i $w $tag $psp 1} err]} {
   if {![string match {OT_CLAND no legal*} $err]} { error $err $::errorInfo }
   cland_put $i $rect $tag $psp 0
  }
 }
 set cland_cursor {}
 foreach pr $rest {cland_put [lindex $pr 1] $rect $tag $psp 1}
 } finally { unset -nocomplain ::cland_pinslot_fit ::cland_xdesc }
 return [list $n [llength $rest] "[expr {$xdesc ? {E face, from the band E edge, } : {}}]stretched over pin y [format %.2f [expr {double($lo)/$ff_dbu}]]..[format %.2f [expr {double($hi)/$ff_dbu}]]"]
}
# FLOW-12 10-30 (COORD 20:4x, DIE-HEAD-45 turn_b pin_reg_p90 92.5 with pinslot on): the +x column form of a ring whose
# bus pins run along x on the face next to the band (turn_b t_i: 566 bits on the N face, band 8.6..164.2 x 608.6..682.6,
# @2.0453) filled every column from the band's far edge to its face edge, 22 slots deep at the band spread, so the
# farthest slot of most bits sat 60..91 um below its pin (pin_reg judges a ring pin at its FARTHEST slot flop); the
# y-column pinslot form never ran there (the +x branch comes first, and its pins are not a y column).  With
# OT_CLAND_PINSLOT=1 such a band now keeps the column form but packs it into a strip on the FACE edge: the n keyed flops
# are dealt in key order over the C columns that fit across the band (flop j -> column floor(j*C/n), so each column
# sits under its own bits' pins); the k-th flop of a column goes k slots (base reserve, spread psp) in from the face
# edge, inside a strip of ceil(1.15*n/C)+1 slots; a taken slot (tapcell, overflow) takes the next free one of its
# column, then of the strip from the nearest columns to its left, then the whole band (first fit, fails closed as before).  Unkeyed flops follow at the band cursor.  Applies only when the pin x order
# follows the key order and the pins lie beyond the band's N or S edge; else it places nothing and returns n = 0 (the
# caller keeps the old column fill).
proc cland_place_pinslot_col {ordered rect tag pins rev {psp 1.0} {rows 2}} {
 global ff_dbu ff_x0 ff_y0 ff_sw ff_rh cland_col_cursor cland_col_reduce
 lassign $rect ax ay bx by
 set rest {}; set al {}
 foreach pr $ordered {
  set k [lindex $pr 0]
  if {![regexp {^[^|]+\|([0-9]+)\|} $k -> kf] || ![dict exists $pins [set bit [cland_kbit $kf $rev]]]} { lappend rest $pr; continue }
  # storage slot (slot field below the 99999999x read/select keys of cland_ffkey) or read register of that bit
  set st [expr {[regexp {^[^|]+\|[0-9]+\|([0-9]+)\|} $k -> ks] && [scan $ks %d] < 999999990}]
  lappend al [list [lindex $pr 1] [dict get $pins $bit] $st]
 }
 set n [llength $al]
 if {!$n} { return [list 0 [llength $ordered] "no keyed flop on a bus pin: old column fill"] }
 set xs [lmap e $al {lindex $e 1 0}]; set ys [lmap e $al {lindex $e 1 1}]
 set lo [lindex $xs 0]; set hi [lindex $xs end]
 set dx [expr {[tcl::mathfunc::max {*}$xs]-[tcl::mathfunc::min {*}$xs]}]
 set dy [expr {[tcl::mathfunc::max {*}$ys]-[tcl::mathfunc::min {*}$ys]}]
 set pyc [expr {[tcl::mathfunc::min {*}$ys]}]; set pyh [expr {[tcl::mathfunc::max {*}$ys]}]
 set ayd [expr {int(ceil($ay*$ff_dbu))}]; set byd [expr {int(floor($by*$ff_dbu))}]
 if {$hi <= $lo || $dx < $dy} { return [list 0 [llength $ordered] "pins not an x row in key order: old column fill"] }
 if {$pyc >= $byd} { set face N } elseif {$pyh <= $ayd} { set face S } else {
  return [list 0 [llength $ordered] "pins not beyond the band's N/S edge: old column fill"]
 }
 set m0 [[lindex $al 0 0] getMaster]
 set rw [expr {int(ceil(double(max([$m0 getWidth],[cland_family_w $m0]))/$ff_sw))*$ff_sw}]
 # vertical pitch: the cell rows plus as many free rows (50 % column density; the write muxes and repair cells sit in
 # the free rows).  The band spread reserve (h/0.4*spread) would make the strip 3+ rows per flop and as deep as the old
 # fill's farthest slots on turn_b (estimate: 22.6 flops per column x 0.81 um -> p90 ~35 um vs 22.6 x 0.54 -> ~28).
 set h0 [$m0 getHeight]
 # rows 1 (AUTOBUILD-PIPE-2 10-31, the +ff band as +x form): every row of the strip (100 % column density), the strip
 # half as deep; the ring's combinational cells go to global placement beside it (S81 t7__cl503f4913 what-if: strip
 # 18.90 -> 9.45 um, pin_reg_p90 30.25 -> 23.97, GRT 0 overflow at 50 iterations)
 set axd [expr {int(ceil($ax*$ff_dbu))}]; set bxd [expr {int(floor($bx*$ff_dbu))}]
 set x0 [expr {$ff_x0+int(ceil(double($axd-$ff_x0)/$ff_sw))*$ff_sw}]
 set nc [expr {max(1,($bxd-$x0)/$rw)}]
 # TYPE-CONS-4 11-07 (OWNER conservative + visual; opt-in, unset = unchanged): OT_CLAND_STRIP_ROWS=n takes every n-th row of
 # the strip, as deep as the band allows.  At rows 1 a 2876-flop ring is ~0.75 flop density plus its logic (coll_ft: 300
 # flops per 10-um bin, density 1.0 under a 0.35 PLACE_DENSITY, because FIRM flops ignore it), and that clump is the GRT
 # overflow; only the pin_reg_p90 target pays (farthest slot ~3x deeper), and targets do not block.
 if {[info exists ::env(OT_CLAND_STRIP_ROWS)] && $::env(OT_CLAND_STRIP_ROWS) > $rows} {
  set q [expr {int(ceil(double($h0)/$ff_rh))*$ff_rh}]
  set fit [expr {($byd-$ayd)/((int(ceil(1.15*$n/$nc))+1)*$q)}]
  set rows [expr {max($rows,min($::env(OT_CLAND_STRIP_ROWS),$fit))}]
  puts "OT_CLAND strip rows $tag: $rows (asked $::env(OT_CLAND_STRIP_ROWS), band fits $fit, $nc columns, $n flops)"
 }
 set rh [expr {$rows*int(ceil(double($h0)/$ff_rh))*$ff_rh}]
 # cland_put_column reserves ceil(h/0.4*spread) rows; its column-capacity reduce takes it down to this pitch
 set red [expr {max(0,int(ceil(double($h0)/0.4*$psp/$ff_rh))-$rh/$ff_rh)}]
 set depth [expr {min($byd-$ayd,(int(ceil(1.15*$n/$nc))+1)*$rh)}]
 if {$face eq "N"} {
  set s0 [expr {$ff_y0+int(floor(double($byd-$depth-$ff_y0)/$ff_rh))*$ff_rh}]; set s0 [expr {max($ayd,$s0)}]; set s1 $byd
 } else { set s0 $ayd; set s1 [expr {min($byd,$ayd+$depth)}] }
 set ::cland_pinslot_fit 1
 set nf 0
 set cland_col_reduce $red
 try {
  # column of flop j (key order) = floor(j*C/n); storage slots take the face rows of their column first, the bit's read
  # registers follow behind them in the same column
  set j 0; set kc [dict create]; set q {}
  foreach e $al { lappend q [list [expr {[lindex $e 2] ? 0 : 1}] $j [lindex $e 0]]; incr j }
  foreach e [lsort -integer -index 0 [lsort -integer -index 1 $q]] {
   set i [lindex $e 2]
   set c [expr {[lindex $e 1]*$nc/$n}]
   set k [expr {[dict exists $kc $c] ? [dict get $kc $c] : 0}]; dict set kc $c [expr {$k+1}]
   # k-th flop of column c: k rows of rh in from the face edge (N: down from the strip top, S: up from its bottom)
   set ty [expr {$face eq "N" ? $s1-($k+1)*$rh : $s0+$k*$rh}]
   set ty [expr {max($s0,$ff_y0+int(floor(double($ty-$ff_y0)/$ff_rh))*$ff_rh)}]
   set w [list [expr {double($x0+$c*$rw)/$ff_dbu}] [expr {double($ty)/$ff_dbu}] $bx [expr {double($s1)/$ff_dbu}]]
   # taken (tapcell, overflow): the strip from 1, 2, 4 .. columns left of c (nearest columns first; a whole-strip
   # first fit from its left end sent turn_b's last bits 160 um away), then the whole band (first fit, fails closed)
   if {[catch {cland_put $i $w $tag $psp 0} err]} {
    set ok 0
    for {set d 1} {!$ok} {set d [expr {2*$d}]} {
     set cl [expr {max(0,$c-$d)}]
     set w [list [expr {double($x0+$cl*$rw)/$ff_dbu}] [expr {double($s0)/$ff_dbu}] $bx [expr {double($s1)/$ff_dbu}]]
     if {![catch {cland_put $i $w $tag $psp 0} err]} { set ok 1 } elseif {![string match {OT_CLAND no legal*} $err]} {
      error $err $::errorInfo
     }
     if {$cl == 0} break
    }
    if {!$ok} { cland_put $i $rect $tag $psp 0; incr nf }
   }
  }
  set cland_col_cursor {}
  unset -nocomplain cland_col_reduce
  foreach pr $rest {cland_put [lindex $pr 1] $rect $tag $psp 1}
 } finally { unset -nocomplain ::cland_pinslot_fit cland_col_reduce; set cland_col_cursor {} }
 return [list $n [llength $rest] "$face face strip [format %.2f [expr {double($s1-$s0)/$ff_dbu}]] um deep, $nc columns over pin x [format %.2f [expr {double($lo)/$ff_dbu}]]..[format %.2f [expr {double($hi)/$ff_dbu}]], $nf by the whole band"]
}
# START is scalar, including the bound-wrapper singleton [0] spelling.  An
# ambiguous or wider inventory is an ABI error, never a choice of nearest bit.
proc cland_start_bterm_name {names bus} {
 set scalar "cland_fstart_in_$bus"
 set singleton "${scalar}\[0\]"
 set found {}
 foreach name $names {
  if {$name eq $scalar || [string first "${scalar}\[" $name] == 0} { lappend found $name }
 }
 if {![llength $found]} { return {} }
 if {[llength $found] != 1 || [lindex $found 0] ni [list $scalar $singleton]} {
  error "OT_CLAND START is not a unique scalar/singleton: $scalar: $found"
 }
 return [lindex $found 0]
}
proc cland_place_ff {prefix rect tag} {
 global ff_blk ff_sw ff_dbu cland_done cland_ff_fill cland_cursor cland_col_cursor cland_col_reduce
 set ffs {};set comb 0;set need 0.0
 foreach i [cland_group_insts $prefix] {
  set nm [$i getName]
  if {[dict exists $cland_done $nm]} continue
  set m [$i getMaster]
  if {[$m isBlock]} { error "OT_CLAND unexpected macro in landing $nm" }
  if {![regexp {DFF|DHL|DLL|SDF} [$m getName]]} { incr comb;continue }
  lappend ffs [list $nm $i]
  set needw [$m getWidth]
  if {[string match {ring:*+x+ff*} $tag] && [info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "resize"} {
   set needw [cland_family_w $m]
  }
  set need [expr {$need+int(ceil(double($needw)/0.4/$ff_sw))*$ff_sw*double([$m getHeight])}]
 }
 if {![llength $ffs]} { return 0 }
 set wch [cland_dsel_wch [lmap pr $ffs {lindex $pr 0}]]
# BEGIN NATIVE_ROLE_BANKS
 if {[info exists ::cland_role_key_context] && [dict exists $::cland_role_key_context $prefix]} {set wch [dict get $::cland_role_key_context $prefix]}
# END NATIVE_ROLE_BANKS
 set rev [string match {ring:*+ffr} $tag]
 set nbits 0; set bus ""
 if {$wch && [regexp {^ring:([^@+]+)} $tag -> bus]} {
  foreach bt [$ff_blk getBTerms] { if {[regexp {^(.*)\[([0-9]+)\]$} [$bt getName] -> bn bi] && $bn eq $bus} { set nbits [expr {max($nbits,$bi+1)}] } }
 }
 set wwc 0; set rwc 0; set tail_groups 0
 if {[info exists ::cland_local_chunks] && [dict exists $::cland_local_chunks $prefix]} {
  set wwc [dict get $::cland_local_chunks $prefix write]
  set rwc [dict get $::cland_local_chunks $prefix read]
 }
 if {[info exists ::cland_local_chunks] && [dict exists $::cland_local_chunks $prefix tail]} {
  set tail_groups [dict get $::cland_local_chunks $prefix tail]
 }
 set ffs [lmap pr $ffs {list [cland_ffkey [lindex $pr 0] $rev $wch $nbits $wwc $rwc $tail_groups] [lindex $pr 1]}]
 # DIE-HEAD-43 c3 (FLOW-11 shared): ring CONTROL registers (raw-name key: counters/ctl/oh/rp/tmo/ready/fault) and
 # status/s_tag keys are keyed right after the bus bit whose pin is nearest the ring's START pin (cland_fstart_in_<bus>)
 # instead of packing first at the band's low corner (HEAD wshim_rx origin->arm_cnt r2r 488 -> 378).  Bands without a
 # START pin or without a storage bus keep the old keys.
 if {[regexp {^ring:([^@+]+)} $tag -> cbus]} {
  set sx {}; set bxy {}
  set start_name [cland_start_bterm_name [lmap bt [$ff_blk getBTerms] {$bt getName}] $cbus]
  foreach bt [$ff_blk getBTerms] {
   set bn [$bt getName]; set bb [$bt getBBox]
   set cx [expr {([$bb xMin]+[$bb xMax])/2}]; set cy [expr {([$bb yMin]+[$bb yMax])/2}]
   if {$bn eq $start_name} { set sx [list $cx $cy] }
   if {[regexp {^(.*)\[([0-9]+)\]$} $bn -> bbn bbi] && $bbn eq $cbus} { lappend bxy [list $bbi $cx $cy] }
  }
  set base {}
  foreach pr $ffs { set k [lindex $pr 0]; if {[regexp {^([^|]+s_d)\|} $k -> b0]} { set base $b0; break } }
  # A separate FREG-only bank has no s_d storage keys from which to infer
  # the bit family. Give it its own family so numeric/reversed pin ordering
  # applies instead of raw ASCII q[0],q[100],... packing.
  if {$base eq {} && [info exists ::cland_numeric_freg_banks] &&
      [dict exists $::cland_numeric_freg_banks $prefix]} { set base "${prefix}/q" }
  if {[llength $bxy] && $base ne {}} {
   set nfb 0; foreach e $bxy { set nfb [expr {max($nfb,[lindex $e 0]+1)}] }
   lassign [cland_freg_rekey $ffs $base $nfb $rev] nfr ffs
   if {$nfr} { puts "OT_CLAND fregkey $prefix: $nfr face registers keyed to their own bus bit" }
  }
  if {[llength $sx] && [llength $bxy] && $base ne {}} {
   lassign [cland_nearest_bit $sx $bxy] best bd
   set kb [expr {$rev ? 999999999-$best : $best}]
   set nbb 0; foreach e $bxy { set nbb [expr {max($nbb,[lindex $e 0]+1)}] }
   lassign [cland_ctl_rekey $ffs $base $kb $nbb $rev] nc ffs
   puts "OT_CLAND ctlkey $prefix: $nc control registers keyed at bit $best (START pin nearest, [format %.1f [expr {$bd/double($ff_dbu)}]] um)"
  }
 }
 if {$wch} { puts "OT_CLAND ring_place=ff $prefix: chunked read registers keyed to their word bits (chunk width $wch, bus $bus width $nbits)" }
 # multi-rect band: the fill spread uses the summed area of its rects
 set barea 0.0; set brects [list $rect]; if {([info exists ::cland_multi] && [dict exists $::cland_multi $tag])} { set brects [dict get $::cland_multi $tag] }
 foreach brect $brects { lassign $brect ax ay bx by; set barea [expr {$barea+($bx-$ax)*($by-$ay)}] }
 lassign $rect ax ay bx by
 set sp [expr {max(1.0,$cland_ff_fill*$barea*$ff_dbu*$ff_dbu/$need)}]
 set cland_cursor {};set cland_col_cursor {}
 set ordered [lsort -dictionary -index 0 $ffs]
 set pinx {}
 if {[string match {ring:*+x+ff*} $tag] && [info exists ::env(OT_CLAND_PINSLOT)] && $::env(OT_CLAND_PINSLOT) eq "1"
     && !([info exists ::cland_multi] && [dict exists $::cland_multi $tag])
     && [regexp {^ring:([^@+]+)} $tag -> pbus] && [dict size [set ppins [cland_bus_pins $pbus]]]} {
  # FLOW-12 10-30: pins along x (N/S face) in key order -> face strip; anything else returns n=0 having placed nothing
  set psp 1.0
  set pinx [cland_place_pinslot_col $ordered $rect $tag $ppins $rev $psp]
  lassign $pinx na nr how
  if {$na} {
   puts "OT_CLAND pinslot $prefix: $na ring flops next to their $pbus bit pin ($how, spread [format %.4f $psp]), $nr by the band cursor"
  } else { puts "OT_CLAND pinslot $prefix: $how" }
 }
 if {[llength $pinx] && [lindex $pinx 0]} {
 } elseif {[string match {ring:*+x+ff*} $tag]} {
  set cland_col_reduce [cland_column_select $ordered $rect $tag $sp]
  puts "OT_CLAND column capacity $prefix: vertical padding reduced by $cland_col_reduce native rows; horizontal reserve unchanged"
  try {
   foreach pr $ordered {cland_put [lindex $pr 1] $rect $tag $sp 1}
  } finally {unset -nocomplain cland_col_reduce}
 } elseif {[info exists ::env(OT_CLAND_PINSLOT)] && $::env(OT_CLAND_PINSLOT) eq "1" && [regexp {^ring:([^@+]+)} $tag -> pbus]
            && !([info exists ::cland_multi] && [dict exists $::cland_multi $tag]) && [dict size [set ppins [cland_bus_pins $pbus]]]} {
  # spread 1.0 (the base w/0.4 reserve): the band spread (tag @<spread>, fill-derived $sp) widens each footprint so a
  # low-corner pack fills its band; the stretched fill already spans the band along the pins, and a wider reserve only
  # pushes each row's later flops away from the face (turn_a what-ifs: fill spread 3.81 -> 3rd flop of a row 38 um
  # off the face; @2.0066 -> 30 um, farthest-slot p90 34.4)
  set psp 1.0
  # AUTOBUILD-PIPE-2 10-31 (S81 slice_station wave 95b1992a3d0, GEOM-85: pin_reg_p90 45..94 on every N/S-face ring): the
  # plan tags those bands +ff/+ffr (no fill_axis x), so only this y-column form ran and refused ("pins not a y column
  # in key order: old fill").  Pins along x beyond the band's N/S edge in key order take the FLOW-12 face-strip column
  # form (the same tag with +x); it places nothing unless that holds, and the y-column form below runs as before.
  set xt [regsub {\+ff(r?)$} $tag {+x+ff\1}]
  set pinx [cland_place_pinslot_col $ordered $rect $xt $ppins $rev $psp 1]
  if {[lindex $pinx 0]} {
   lassign $pinx na nr how
   puts "OT_CLAND pinslot $prefix: $na ring flops next to their $pbus bit pin ($how, +ff band as +x, spread [format %.4f $psp]), $nr by the band cursor"
  } else {
  # DIE-KV-62/stations 11-02 opt-in OT_CLAND_PINSLOT_DENSE=1 (plan budgets.cland_pinslot_dense_types): the y-column
  # rows reserve only each flop's own body (spread 0.4 = w/0.4*0.4), so the 5+ slot flops of a bit sit side by side
  # from the pin-side edge instead of 2.5 bodies apart (KV kv3_io_ft_v1 E/W 523-bit rings, 8.4 flops per row: strip
  # 22.7 -> 9 um, farthest-slot pin_reg p90 39.6 -> 27.3 um, wave synth+floorplan probe).  The widest-drive fit
  # (cland_pinslot_fit) still keeps every in-place GPL upsize legal; the ring logic stays with GPL.  Unset = unchanged.
  set ypsp [expr {[info exists ::env(OT_CLAND_PINSLOT_DENSE)] && $::env(OT_CLAND_PINSLOT_DENSE) eq "1" ? 0.4 : $psp}]
  # TYPE-CONS-4 11-07: OT_CLAND_STRIP_ROWS=n also widens the y-column form to n flop bodies per slot, capped by the band's
  # fill spread (sp): KV hroot, 5730 ring flops, 47-um band, was a 9-um wall at the E edge, density 0.7 before its logic.
  if {[info exists ::env(OT_CLAND_STRIP_ROWS)]} {
   set ypsp0 $ypsp
   set ypsp [expr {max($ypsp,min(0.4*$::env(OT_CLAND_STRIP_ROWS),$sp))}]
   puts "OT_CLAND strip rows $tag: y-column spread [format %.4f $ypsp0] -> [format %.4f $ypsp] (band fill spread [format %.4f $sp])"
  }
  lassign [cland_place_pinslot $ordered $rect $tag $sp $ppins $rev $ypsp] na nr how
  puts "OT_CLAND pinslot $prefix: $na ring flops next to their $pbus bit pin ($how, spread [format %.4f $ypsp]), $nr by the band cursor"
  }
 } else {
  set sp [cland_fill_spread $ordered $rect $tag $sp]
  foreach pr $ordered {cland_put [lindex $pr 1] $rect $tag $sp 1}
 }
 set cland_cursor {};set cland_col_cursor {}
 puts "OT_CLAND ring_place=ff $prefix: [llength $ffs] ring flops FIRM bit-major at spread [format %.4f $sp], $comb ring logic cells left to global placement"
 return [llength $ffs]
}
# FLOW-KITFAIL-3 10-29 (S81-KITS-B iqf__t1, plan_s13r2 band_ring=all): an all-cells ring whose reserved footprints
# cannot fit its band still ran the first-fit cland_put cell by cell (each call rescans from the band corner, O(n^2):
# 5,154 of 30,520 ft1_i cells in 40 min) before the certain "no legal nonoverlapping row/site" error.  The same error is
# raised up front when the group's reserved area (w/0.4*spread per cell, as cland_put reserves it) exceeds an upper
# bound of what the band can hold: per band row, every free segment (length >= the narrowest body) plus one widest
# reservation of overhang at its end (a last body fits, its reservation may run past the segment).  Bands that fit,
# multi-row cells and bands not inside the core skip it: their placement is unchanged.
proc cland_band_fit {prefix rect tag} {
 global ff_blk ff_x0 ff_y0 ff_x1 ff_y1 ff_rh ff_sw ff_dbu ff_orient cland_occ cland_done
 set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp
 set need 0.0; set maxrw 0; set minw {}; set n 0
 foreach i [cland_group_insts $prefix] {
  set nm [$i getName]
  if {[dict exists $cland_done $nm]} continue
  set m [$i getMaster]
  if {[$m isBlock]} return
  set w [$m getWidth]; set h [$m getHeight]
  if {$h > $ff_rh} return
  set rw [expr {int(ceil(double($w)/0.4*$sp/$ff_sw))*$ff_sw}]
  set need [expr {$need + double($rw)*$ff_rh}]
  if {$rw > $maxrw} { set maxrw $rw }
  if {$minw eq {} || $w < $minw} { set minw $w }
  incr n
 }
 if {!$n} return
 # multi-rect band: the upper bound is the sum over its rects (one rect: the loop body runs once, unchanged)
 set cap 0.0
 set brects [list $rect]; if {([info exists ::cland_multi] && [dict exists $::cland_multi $tag])} { set brects [dict get $::cland_multi $tag] }
 foreach brect $brects {
 lassign $brect ax ay bx by
 set ax [expr {int(ceil($ax*$ff_dbu))}];set ay [expr {int(ceil($ay*$ff_dbu))}]
 set bx [expr {int(floor($bx*$ff_dbu))}];set by [expr {int(floor($by*$ff_dbu))}]
 if {$ax < $ff_x0 || $ay < $ff_y0 || $bx > $ff_x1 || $by > $ff_y1} return
 set startx [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set starty [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 for {set y $starty} {$y+$ff_rh<=$by} {incr y $ff_rh} {
  if {![dict exists $ff_orient $y]} continue
  set r [expr {int(($y-$ff_y0)/$ff_rh)}]
  set occ {}
  if {[dict exists $cland_occ $r]} { set occ [lsort -integer -index 0 [dict get $cland_occ $r]] }
  set x $startx
  foreach iv [concat $occ [list [list $bx $bx]]] {
   lassign $iv l u
   set e [expr {min($l,$bx)}]
   if {$e - $x >= $minw} { set cap [expr {$cap + double($e - $x + $maxrw)*$ff_rh}] }
   if {$u > $x} { set x $u }
   if {$x >= $bx} break
  }
 }
 }
 if {$need > $cap} {
  set a2 [expr {double($ff_dbu)*$ff_dbu}]
  error [format "OT_CLAND no legal nonoverlapping row/site in reserved band for %s (%s): %d cells reserve %.1f um2 > band upper bound %.1f um2 (ratio %.2f), checked before placement" $prefix $tag $n [expr {$need/$a2}] [expr {$cap/$a2}] [expr {$cap > 0 ? $need/$cap : 0}]]
 }
}
# AUTOBUILD-PIPE-2 10-31 (S81 slice_station wave, event 95b1992a3d0: 7 of 7 place FAILs "no legal ... (collector:rst_rl_N)"):
# a reset-collector window is its relay xy +-2.16 um, but the plan's reset tree puts 2..6 relays on ONE xy (t42
# rst_rl_146/147, t40 rst_rl_162..165: identical windows) or the relay inside a ring band the FIRM ring fill already
# took (t21 rst_n_t8 in ft5_i).  A collector cell with no site in its window takes the window grown about the same
# centre x2, x4, x8 (<= +-17.28 um; a reset status hop, far below the 405 um relay reach); still none fails closed as
# before.  Rings, status, start relays and every collector that fits its window are unchanged.
# BEGIN NATIVE_ROLE_BANKS
# Opt-in native clock/data-role banks. All membership checks finish before any bank moves.
proc cland_role_lib_clocks {i} {
 global cland_role_lib_cache
 set master [[$i getMaster] getName]
 if {[dict exists $cland_role_lib_cache $master]} {return [dict get $cland_role_lib_cache $master]}
 set cell [get_cells -quiet [list [$i getName]]]
 if {[llength $cell] != 1} {error "OT_CLAND_ROLE ambiguous native STA cell [$i getName]"}
 set lc [get_lib_cells -quiet -of_objects $cell]
 if {[llength $lc] != 1} {error "OT_CLAND_ROLE missing native Liberty cell $master"}
 set clocks {}
 foreach lp [get_lib_pins -quiet -of_objects $lc] {
  if {[get_property $lp is_clock]} {lappend clocks [get_property $lp name]}
 }
 dict set cland_role_lib_cache $master [lsort -unique $clocks]
 return [dict get $cland_role_lib_cache $master]
}
proc cland_role_first_capture {net} {
 global cland_role_capture_cache cland_role_capture_visiting cland_role_input_ports
 if {$net eq "NULL" || $net eq ""} {error "OT_CLAND_ROLE disconnected data pin"}
 if {[dict exists $cland_role_capture_cache $net]} {return [dict get $cland_role_capture_cache $net]}
 if {[dict exists $cland_role_capture_visiting $net]} {error "OT_CLAND_ROLE combinational data cycle"}
 dict set cland_role_capture_visiting $net 1
 set drivers {}
 foreach bt [$net getBTerms] {
  if {[$bt getIoType] eq "INPUT"} {lappend drivers [list port $bt]}
  if {[$bt getIoType] eq "INOUT"} {error "OT_CLAND_ROLE inout data source [$bt getName]"}
 }
 foreach it [$net getITerms] {
  set mt [$it getMTerm]
  if {[$mt getSigType] in {POWER GROUND}} continue
  if {[$mt getIoType] eq "OUTPUT"} {lappend drivers [list inst [$it getInst]]}
  if {[$mt getIoType] eq "INOUT"} {error "OT_CLAND_ROLE inout data pin [$mt getName]"}
 }
 if {[llength $drivers] != 1} {error "OT_CLAND_ROLE missing/multiple native data driver [$net getName]"}
 lassign [lindex $drivers 0] kind obj
 set ports {}
 if {$kind eq "port"} {
  set name [$obj getName]
  if {[dict exists $cland_role_input_ports $name]} {lappend ports $name}
 } elseif {![llength [cland_role_lib_clocks $obj]]} {
  if {[[$obj getMaster] isBlock]} {error "OT_CLAND_ROLE opaque macro in first-capture cone [$obj getName]"}
  foreach it [$obj getITerms] {
   set mt [$it getMTerm]
   if {[$mt getIoType] eq "INPUT" && [$mt getSigType] ni {POWER GROUND}} {
    lappend ports {*}[cland_role_first_capture [$it getNet]]
   }
  }
 }
 dict unset cland_role_capture_visiting $net
 dict set cland_role_capture_cache $net [lsort -unique $ports]
 return [dict get $cland_role_capture_cache $net]
}
proc cland_role_prepare {prefix cfg} {
 global ff_blk cland_done cland_role_input_ports cland_role_capture_cache cland_role_capture_visiting cland_role_seen
 set roles [dict get $cfg roles];set bus [dict get $cfg bus]
 set cland_role_input_ports {};set cland_role_capture_cache {};set cland_role_capture_visiting {}
 foreach bt [$ff_blk getBTerms] {
  if {[$bt getIoType] eq "INPUT" && [regexp [format {^%s\[[0-9]+\]$} $bus] [$bt getName]]} {
   dict set cland_role_input_ports [$bt getName] 0
  }
 }
 if {![dict size $cland_role_input_ports]} {error "OT_CLAND_ROLE missing actual input bus $bus"}
 set held {};set sources {};set members {};set first {};set rectangles {}
 foreach row [dict get $cfg held] {
  lassign $row name master port
  if {[dict exists $held $name]} {error "OT_CLAND_ROLE duplicate held member $name"}
  dict set held $name [list $master $port]
 }
 foreach row [dict get $cfg banks] {
  lassign $row name port filter expected expected_first rect qualified
  dict set members $name {};dict set first $name 0;dict set rectangles $name $rect
  dict set expected_native $name $qualified
  dict set sources $port {}
 }
 dict for {name pair} $held {dict set sources [lindex $pair 1] {}}
 dict for {port unused} $sources {
  set bt [$ff_blk findBTerm $port]
  if {$bt eq "NULL" || $bt eq "" || [$bt getIoType] ne "INPUT" || [$bt getNet] eq "NULL"} {
   error "OT_CLAND_ROLE missing exact native clock source $port"
  }
  set net [$bt getNet]
  dict for {other connected} $sources {
   if {$other ne $port && $connected ne {} && $connected eq $net} {error "OT_CLAND_ROLE aliased native clock sources $port/$other"}
  }
  dict set sources $port $net
 }
 set all {};set found_held {};set first_ports {};set held_insts {}
 set native_group [cland_group_insts $prefix]
 foreach i $native_group {
  set clocks [cland_role_lib_clocks $i]
  if {![llength $clocks]} continue
  set name [$i getName];set master [[$i getMaster] getName]
  if {[dict exists $cland_role_seen $name]} {error "OT_CLAND_ROLE duplicate native member $name"}
  dict set cland_role_seen $name $prefix
  if {![dict exists $roles $master]} {error "OT_CLAND_ROLE unknown sequential master $master ($name)"}
  if {![regexp {DFF|DHL|DLL|SDF} $master]} {error "OT_CLAND_ROLE unsupported legacy FF placer master $master"}
  set role [dict get $roles $master];set cp [dict get $role clock]
  if {$clocks ne [list $cp]} {error "OT_CLAND_ROLE unqualified clock-pin roles $name"}
  set inputs {}
  foreach it [$i getITerms] {
   set mt [$it getMTerm]
   if {[$mt getIoType] eq "INPUT" && [$mt getSigType] ni {POWER GROUND}} {lappend inputs [$mt getName]}
  }
  set expected [concat [list $cp] [dict get $role data] [dict get $role reset]]
  if {[lsort $inputs] ne [lsort $expected]} {error "OT_CLAND_ROLE unqualified data/reset pin roles $name"}
  set it [$i findITerm $cp];set net [$it getNet];set root {}
  dict for {port connected} $sources {if {$net ne "NULL" && $net eq $connected} {lappend root $port}}
  if {[llength $root] != 1} {error "OT_CLAND_ROLE unknown/buffered native clock source $name"}
  set root [lindex $root 0];set capture {}
  foreach dp [dict get $role data] {lappend capture {*}[cland_role_first_capture [[$i findITerm $dp] getNet]]}
  set capture [lsort -unique $capture]
  if {[llength $capture] > 1} {error "OT_CLAND_ROLE first capture spans multiple bus bits $name"}
  lappend all $name
  if {[dict exists $held $name]} {
   if {[dict get $held $name] ne [list $master $root] || [llength $capture] || [$i getPlacementStatus] ni {FIRM LOCKED}} {
    error "OT_CLAND_ROLE held status identity/role/placement mismatch $name"
   }
   dict set found_held $name 1;lappend held_insts $i;continue
  }
  if {[dict exists $cland_done $name]} {error "OT_CLAND_ROLE native member already placed $name"}
  set matches {}
  foreach row [dict get $cfg banks] {
   lassign $row bank port filter expected expected_first rect qualified
   if {$port eq $root && ($filter eq "any" || ($filter eq "present" && [llength $capture]) || ($filter eq "absent" && ![llength $capture]))} {lappend matches $bank}
  }
  if {[llength $matches] != 1} {error "OT_CLAND_ROLE unknown/duplicate bank membership $name"}
  set bank [lindex $matches 0]
  if {![dict exists $expected_native $bank $name] || [dict get $expected_native $bank $name] ne $master} {error "OT_CLAND_ROLE unknown/replaced native member $name"}
  dict lappend members $bank $i
  if {[llength $capture]} {dict incr first $bank;dict incr first_ports [lindex $capture 0]}
 }
 if {[llength $all] != [dict get $cfg total] || [dict size $found_held] != [dict size $held]} {
  error "OT_CLAND_ROLE missing/extra qualified native or held members $prefix"
 }
 foreach row [dict get $cfg banks] {
  lassign $row bank port filter expected expected_first rect qualified
  if {[llength [dict get $members $bank]] != $expected || [dict get $first $bank] != $expected_first} {
   error "OT_CLAND_ROLE qualified member/first-capture count mismatch $prefix/$bank"
  }
 }
 dict for {port unused} $cland_role_input_ports {
  if {![dict exists $first_ports $port] || [dict get $first_ports $port] != [dict get $cfg captures_per_port]} {
   error "OT_CLAND_ROLE missing/duplicate first-capture slot for $port"
  }
 }
 return [dict create members $members held $held_insts wch [cland_dsel_wch $all]]
}
proc cland_role_place {prefix tag} {
 global cland_multi cland_done
 set cfg [dict get $::cland_native_role_banks $prefix]
 if {[dict exists $::cland_role_placed $prefix]} {error "OT_CLAND_ROLE duplicate bank placement $prefix"}
 dict for {bank members} [dict get $::cland_role_prepared $prefix members] {
  foreach i $members {if {[dict exists $cland_done [$i getName]]} {error "OT_CLAND_ROLE member placed before bank $prefix/[$i getName]"}}
 }
 rename cland_group_insts cland_role_unfiltered_group_insts
 proc cland_group_insts {prefix} {
  if {[info exists ::cland_role_active_members] && [dict exists $::cland_role_active_members $prefix]} {return [dict get $::cland_role_active_members $prefix]}
  return [cland_role_unfiltered_group_insts $prefix]
 }
 set saved_multi $cland_multi
 dict unset cland_multi $tag
 dict set ::cland_role_key_context $prefix [dict get $::cland_role_prepared $prefix wch]
 try {
  foreach row [dict get $cfg banks] {
   lassign $row bank port filter expected expected_first rect qualified
   dict set ::cland_role_active_members $prefix [dict get $::cland_role_prepared $prefix members $bank]
   if {[cland_place_ff $prefix $rect $tag] != $expected} {error "OT_CLAND_ROLE placed count mismatch $prefix/$bank"}
   puts "OT_CLAND_ROLE $prefix/$bank: $expected native members ($expected_first first captures), source $port"
  }
 } finally {
  set cland_multi $saved_multi
  dict unset ::cland_role_key_context $prefix
  dict unset ::cland_role_active_members $prefix
  rename cland_group_insts {};rename cland_role_unfiltered_group_insts cland_group_insts
 }
 dict set ::cland_role_placed $prefix 1
}
if {[info exists ::cland_native_role_banks] && [dict size $::cland_native_role_banks]} {
 set cland_role_lib_cache {};set cland_role_seen {};set cland_role_prepared {};set cland_role_placed {}
 dict for {prefix cfg} $::cland_native_role_banks {dict set cland_role_prepared $prefix [cland_role_prepare $prefix $cfg]}
 # Every bank is validated. Reserve the already-sited status FFs without moving them.
 dict for {prefix prepared} $cland_role_prepared {
  foreach i [dict get $prepared held] {
   set bb [$i getBBox]
   cland_occupy [$bb xMin] [$bb yMin] [expr {[$bb xMax]-[$bb xMin]}] [expr {[$bb yMax]-[$bb yMin]}]
  }
 }
}
# END NATIVE_ROLE_BANKS
set cland_multi_seen {}
foreach spec $cland_groups {
 lassign $spec prefix rect tag
# BEGIN NATIVE_ROLE_BANKS
 if {[info exists ::cland_native_role_banks] && [dict exists $::cland_native_role_banks $prefix]} {
  if {![dict exists $::cland_role_placed $prefix]} {cland_role_place $prefix $tag}
  continue
 }
# END NATIVE_ROLE_BANKS
 # multi-rect band: its first entry places the whole ring over all its rects; the later entries are the same group
 if {[dict exists $cland_multi $tag]} {
  if {[dict exists $cland_multi_seen $tag]} continue
  dict set cland_multi_seen $tag 1
 }
 set hit 0
 if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]} {
  if {![cland_place_ff $prefix $rect $tag]} { error "OT_CLAND no mapped ring flops found under $prefix" }
  continue
 }
 set coll [string match {collector:*} $tag]
 if {!$coll} { cland_band_fit $prefix $rect $tag }
 foreach i [cland_group_insts $prefix] {
  set nm [$i getName]
  if {[dict exists $cland_done $nm]} continue
  if {[[$i getMaster] isBlock]} { error "OT_CLAND unexpected macro in landing $nm" }
  # DQ87 11-07 (QC slw_fe_v1): a 4.32-um local reset window can be all FIRM face flops; this one-load flop may stand further off.
  # DIE-QC-97 11-09: reader/writer START relay windows take the status/collector grow (cland_put_start).
  # KW43 LAND-RESERVE (opt-in OT_LAND_RESERVE=1): a literal local reset window grows like local-reset; the dispatch below is unchanged
 if {!$coll && $tag eq "literal-local-reset" && [info exists ::env(OT_LAND_RESERVE)] && $::env(OT_LAND_RESERVE) eq "1"} { cland_put_grow $i $rect $tag literal-reset; incr hit; continue }
 if {$coll} { cland_put_collector $i $rect $tag } elseif {$tag eq "local-reset"} { cland_put_grow $i $rect $tag local-reset } elseif {[string match {reader-start:*} $tag] || [string match {writer-start:*} $tag]} { cland_put_start $i $rect $tag } else { cland_put $i $rect $tag };incr hit
 }
 if {!$hit} { error "OT_CLAND no mapped cells found under $prefix" }
}
close $cland_fh
puts "OT_CLAND placed $cland_n actual mapped cells FIRM in nonoverlapping reserved bands/relay sites"
# DIE-HEAD-42 V1: landed stations of plan-siteless bits follow their now-placed ring fan-in (face_flops.tcl)
if {[info exists ff_landed_line] && [llength $ff_landed_line] && [llength [info procs ff_landed_line_place]]} { ff_landed_line_place }
# AUTOBUILD-PIPE-2 (AUTOBUILD-GATE-1 handoff, S81 slice_station t14/t26 r2r 580-677 um): reset_taps.tcl re-pointed every
# FIRM flop's reset to its nearest tap BEFORE the landed line moved stations s0..s<k-2> (eq epoch flops went ~580 um
# from their reset leaf u_rrl_<k>).  Re-point only the moved stations again, now at their final sites.
if {[info exists ff_landed_moved] && [llength $ff_landed_moved] && [file exists /work/reset_taps.tcl]} {
  set rt_repoint_only [dict create]
  foreach n $ff_landed_moved { dict set rt_repoint_only $n 1 }
  source /work/reset_taps.tcl
  unset rt_repoint_only
}
