# Generated caller provides cland_groups: {prefix rect tag}, and
# cland_status: {net x y}. Called after existing face/reset/FT FIRM sites.
if {![info exists ff_blk] || ![info exists ff_dbu]} { error "OT_CLAND missing face placement context" }
set cland_occ {}; set cland_done {}; set cland_n 0
proc cland_ours {name} { return [regexp {(^|[/.])u_cland_} $name] }
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
 if {[info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "1"} {
  set fsp $sp; if {$fsp eq {}} { set fsp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> fsp }
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
   if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED }
   $i setOrient [dict get $ff_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
   # Reserve spacing as well as the real body. Density margin permits the
   # datapath mux/control cells and leaves room for clock/reset repair.
   # DIE-HEAD-12 opt-in band spread: tag ring:<bus>@<spread> widens the reserved footprint so the ring fills its band
   if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }
   set rw [expr {int(ceil(double($w)/0.4*$sp/$ff_sw))*$ff_sw}]
   cland_occupy $x $y $rw $h
   if {$cur} { set cland_cursor [list $y [expr {$x+$rw}]] }
   dict set cland_done $name 1;incr cland_n
   puts $cland_fh "$name\tcland:$tag\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\t-"
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
# Registered status outputs sit at their declared source point, separately
# from the ring storage band; the collector then follows its original tree.
foreach spec $cland_status {
 lassign $spec net x y
 set n [$ff_blk findNet $net]
 if {$n eq "NULL"} {
  # DIE-KV-32 10-29 (KV hroot 3_3_place_gp): a --kit-rtl kit flattens the bound wrapper, so the status net carries
  # its instance prefix (u_bound.landing_ready_ft0_i), as the ring groups above already allow ((^|[/.])prefix).
  # Exactly one hierarchical match is taken; none or several stay errors (fail closed).
  set cland_cand {}; set cland_l [string length $net]
  foreach cland_x [$ff_blk getNets] {
   set cland_nm [$cland_x getName]
   if {[string length $cland_nm] > $cland_l && [string range $cland_nm end-[expr {$cland_l-1}] end] eq $net
       && [string index $cland_nm end-$cland_l] in {. /}} { lappend cland_cand $cland_x }
  }
  if {[llength $cland_cand] == 1} { set n [lindex $cland_cand 0] } elseif {[llength $cland_cand] > 1} {
   error "OT_CLAND ambiguous status net $net: [llength $cland_cand] hierarchical matches"
  }
 }
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
 if {[llength $drivers]!=1 || ![string match "*DFF*" [[[lindex $drivers 0] getMaster] getName]]} {
  error "OT_CLAND $net requires one actual dedicated output FF"
 }
 cland_put [lindex $drivers 0] [list [expr {$x-2.16}] [expr {$y-2.16}] [expr {$x+2.16}] [expr {$y+2.16}]] status:$net
}
foreach spec $cland_optional_groups {
 lassign $spec prefix rect tag
 foreach i [$ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
  if {[dict exists $cland_done $nm]} continue
  cland_put $i $rect $tag
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
proc cland_ffkey {nm {rev 0} {wch 0} {nbits 0}} {
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
  if {$kind eq "y"} { set bit [expr {$c*$wch+$i}]; set s 999999998 } else { set bit [expr {$c*$wch+$wch/2}]; set s [expr {999999990+$i}] }
  if {$nbits > 0 && $bit >= $nbits} { return $nm }
  if {$rev} { set bit [expr {999999999-$bit}] }
  return [format {%s|%09d|%09d|%s} "${b}s_d" $bit $s $t]
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
proc cland_dsel_wch {names} {
 set w 0
 foreach nm $names {
  if {[regexp {[/.]dch\\?\[[0-9]+\\?\]\.u_dsel/y\\?\[([0-9]+)\\?\]} $nm -> i]} { set w [expr {max($w,$i+1)}] }
 }
 return $w
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
  foreach pr $ordered {cland_put [lindex $pr 1] $rect $tag $sp 1}
  return [list 0 [llength $ordered] "pins not a y column in key order: old fill"]
 }
 # the stretched rows sit at the plan spread, tighter than the fill spread: fit each flop on its widest drive variant
 # (as OT_CLAND_FIT_RESERVE=resize) so the in-place GPL upsize cannot grow over a tapcell (turn_a what-if without it:
 # 3_5 DPL-0033, 55 ring DFFHQNx1 -> x2 over TAPCELLs)
 set ::cland_pinslot_fit 1
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
 } finally { unset -nocomplain ::cland_pinslot_fit }
 return [list $n [llength $rest] "stretched over pin y [format %.2f [expr {double($lo)/$ff_dbu}]]..[format %.2f [expr {double($hi)/$ff_dbu}]]"]
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
proc cland_place_pinslot_col {ordered rect tag pins rev {psp 1.0}} {
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
 set rh [expr {2*int(ceil(double($h0)/$ff_rh))*$ff_rh}]
 # cland_put_column reserves ceil(h/0.4*spread) rows; its column-capacity reduce takes it down to this pitch
 set red [expr {max(0,int(ceil(double($h0)/0.4*$psp/$ff_rh))-$rh/$ff_rh)}]
 set axd [expr {int(ceil($ax*$ff_dbu))}]; set bxd [expr {int(floor($bx*$ff_dbu))}]
 set x0 [expr {$ff_x0+int(ceil(double($axd-$ff_x0)/$ff_sw))*$ff_sw}]
 set nc [expr {max(1,($bxd-$x0)/$rw)}]
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
proc cland_place_ff {prefix rect tag} {
 global ff_blk ff_sw ff_dbu cland_done cland_ff_fill cland_cursor cland_col_cursor cland_col_reduce
 set ffs {};set comb 0;set need 0.0
 foreach i [$ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
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
 set rev [string match {ring:*+ffr} $tag]
 set nbits 0; set bus ""
 if {$wch && [regexp {^ring:([^@+]+)} $tag -> bus]} {
  foreach bt [$ff_blk getBTerms] { if {[regexp {^(.*)\[([0-9]+)\]$} [$bt getName] -> bn bi] && $bn eq $bus} { set nbits [expr {max($nbits,$bi+1)}] } }
 }
 set ffs [lmap pr $ffs {list [cland_ffkey [lindex $pr 0] $rev $wch $nbits] [lindex $pr 1]}]
 # DIE-HEAD-43 c3 (FLOW-11 shared): ring CONTROL registers (raw-name key: counters/ctl/oh/rp/tmo/ready/fault) and
 # status/s_tag keys are keyed right after the bus bit whose pin is nearest the ring's START pin (cland_fstart_in_<bus>)
 # instead of packing first at the band's low corner (HEAD wshim_rx origin->arm_cnt r2r 488 -> 378).  Bands without a
 # START pin or without a storage bus keep the old keys.
 if {[regexp {^ring:([^@+]+)} $tag -> cbus]} {
  set sx {}; set bxy {}
  foreach bt [$ff_blk getBTerms] {
   set bn [$bt getName]; set bb [$bt getBBox]
   set cx [expr {([$bb xMin]+[$bb xMax])/2}]; set cy [expr {([$bb yMin]+[$bb yMax])/2}]
   if {$bn eq "cland_fstart_in_$cbus"} { set sx [list $cx $cy] }
   if {[regexp {^(.*)\[([0-9]+)\]$} $bn -> bbn bbi] && $bbn eq $cbus} { lappend bxy [list $bbi $cx $cy] }
  }
  set base {}
  foreach pr $ffs { set k [lindex $pr 0]; if {[regexp {^([^|]+s_d)\|} $k -> b0]} { set base $b0; break } }
  if {[llength $sx] && [llength $bxy] && $base ne {}} {
   lassign [cland_nearest_bit $sx $bxy] best bd
   set kb [expr {$rev ? 999999999-$best : $best}]
   set nbb 0; foreach e $bxy { set nbb [expr {max($nbb,[lindex $e 0]+1)}] }
   lassign [cland_ctl_rekey $ffs $base $kb $nbb $rev] nc ffs
   puts "OT_CLAND ctlkey $prefix: $nc control registers keyed at bit $best (START pin nearest, [format %.1f [expr {$bd/double($ff_dbu)}]] um)"
  }
 }
 if {$wch} { puts "OT_CLAND ring_place=ff $prefix: chunked read registers keyed to their word bits (chunk width $wch, bus $bus width $nbits)" }
 lassign $rect ax ay bx by
 set sp [expr {max(1.0,$cland_ff_fill*($bx-$ax)*($by-$ay)*$ff_dbu*$ff_dbu/$need)}]
 set cland_cursor {};set cland_col_cursor {}
 set ordered [lsort -dictionary -index 0 $ffs]
 set pinx {}
 if {[string match {ring:*+x+ff*} $tag] && [info exists ::env(OT_CLAND_PINSLOT)] && $::env(OT_CLAND_PINSLOT) eq "1"
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
            && [dict size [set ppins [cland_bus_pins $pbus]]]} {
  # spread 1.0 (the base w/0.4 reserve): the band spread (tag @<spread>, fill-derived $sp) widens each footprint so a
  # low-corner pack fills its band; the stretched fill already spans the band along the pins, and a wider reserve only
  # pushes each row's later flops away from the face (turn_a what-ifs: fill spread 3.81 -> 3rd flop of a row 38 um
  # off the face; @2.0066 -> 30 um, farthest-slot p90 34.4)
  set psp 1.0
  lassign [cland_place_pinslot $ordered $rect $tag $sp $ppins $rev $psp] na nr how
  puts "OT_CLAND pinslot $prefix: $na ring flops next to their $pbus bit pin ($how, spread [format %.4f $psp]), $nr by the band cursor"
 } else {
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
 foreach i [$ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
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
 lassign $rect ax ay bx by
 set ax [expr {int(ceil($ax*$ff_dbu))}];set ay [expr {int(ceil($ay*$ff_dbu))}]
 set bx [expr {int(floor($bx*$ff_dbu))}];set by [expr {int(floor($by*$ff_dbu))}]
 if {$ax < $ff_x0 || $ay < $ff_y0 || $bx > $ff_x1 || $by > $ff_y1} return
 set startx [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set starty [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 set cap 0.0
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
 if {$need > $cap} {
  set a2 [expr {double($ff_dbu)*$ff_dbu}]
  error [format "OT_CLAND no legal nonoverlapping row/site in reserved band for %s (%s): %d cells reserve %.1f um2 > band upper bound %.1f um2 (ratio %.2f), checked before placement" $prefix $tag $n [expr {$need/$a2}] [expr {$cap/$a2}] [expr {$cap > 0 ? $need/$cap : 0}]]
 }
}
foreach spec $cland_groups {
 lassign $spec prefix rect tag
 set hit 0
 if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]} {
  if {![cland_place_ff $prefix $rect $tag]} { error "OT_CLAND no mapped ring flops found under $prefix" }
  continue
 }
 cland_band_fit $prefix $rect $tag
 foreach i [$ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
  if {[dict exists $cland_done $nm]} continue
  if {[[$i getMaster] isBlock]} { error "OT_CLAND unexpected macro in landing $nm" }
  cland_put $i $rect $tag;incr hit
 }
 if {!$hit} { error "OT_CLAND no mapped cells found under $prefix" }
}
close $cland_fh
puts "OT_CLAND placed $cland_n actual mapped cells FIRM in nonoverlapping reserved bands/relay sites"
# DIE-HEAD-42 V1: landed stations of plan-siteless bits follow their now-placed ring fan-in (face_flops.tcl)
if {[info exists ff_landed_line] && [llength $ff_landed_line] && [llength [info procs ff_landed_line_place]]} { ff_landed_line_place }
