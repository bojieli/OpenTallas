# Generated caller provides cland_groups: {prefix rect tag}, and
# cland_status: {net x y}. Called after existing face/reset/FT FIRM sites.
if {![info exists ff_blk] || ![info exists ff_dbu]} { error "OT_CLAND missing face placement context" }
set cland_occ {}; set cland_done {}; set cland_n 0
proc cland_ours {name} { return [regexp {(^|[/.])u_cland_} $name] }
proc cland_occupy {x y w h} {
 global cland_occ ff_y0 ff_rh
 set r0 [expr {int(floor(double($y-$ff_y0)/$ff_rh))}]
 set r1 [expr {int(ceil(double($y+$h-$ff_y0)/$ff_rh))}]
 for {set r $r0} {$r<$r1} {incr r} { dict lappend cland_occ $r [list $x [expr {$x+$w}]] }
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
# DIE-HEAD-13 opt-in: sp = reserve spread given by the caller (else from the tag), cur = resume the row scan at the last
# site this band placed (ordered fill: O(n) instead of the O(n^2) rescan from the band corner). Defaults unchanged.
proc cland_put {i rect tag {sp {}} {cur 0}} {
 global ff_x0 ff_y0 ff_x1 ff_y1 ff_rh ff_sw ff_dbu ff_orient cland_occ cland_done cland_n cland_fh cland_cursor
 set name [$i getName]
 if {[dict exists $cland_done $name]} { error "OT_CLAND duplicate placement $name" }
 lassign $rect ax ay bx by
 set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
 set ax [expr {int(ceil($ax*$ff_dbu))}];set ay [expr {int(ceil($ay*$ff_dbu))}]
 set bx [expr {int(floor($bx*$ff_dbu))}];set by [expr {int(floor($by*$ff_dbu))}]
 # FLOW-GEN-1 10-28 (DIE-HEAD-9 bug 5): a window centred within half its size of the core edge (a status pin in the
 # core margin) clips to less than the cell; slide it, same size, inside the core (windows that fit are unchanged,
 # windows farther out still fail closed)
 set ov [expr {min($bx,$ff_x1)-max($ax,$ff_x0)}]
 if {$ov < $w && $bx-$ax >= $w && 2*$ov >= $ax-$bx} {
  if {$ax < $ff_x0} { set bx [expr {$bx+$ff_x0-$ax}];set ax $ff_x0 } elseif {$bx > $ff_x1} { set ax [expr {$ax-($bx-$ff_x1)}];set bx $ff_x1 }
 }
 set ov [expr {min($by,$ff_y1)-max($ay,$ff_y0)}]
 if {$ov < $h && $by-$ay >= $h && 2*$ov >= $ay-$by} {
  if {$ay < $ff_y0} { set by [expr {$by+$ff_y0-$ay}];set ay $ff_y0 } elseif {$by > $ff_y1} { set ay [expr {$ay-($by-$ff_y1)}];set by $ff_y1 }
 }
 set ax [expr {max($ff_x0,$ax)}];set ay [expr {max($ff_y0,$ay)}]
 set bx [expr {min($ff_x1,$bx)}];set by [expr {min($ff_y1,$by)}]
 set startx [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set starty [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 if {$cur && [llength $cland_cursor]==2} { lassign $cland_cursor cy cx; if {$cy>$starty} { set starty $cy } } else { set cy {} }
 # DIE-KV-33 opt-in OT_CLAND_FIT_RESERVE=1: the site must be free of other occupancy over the whole reserved footprint
 # (rw, as cland_occupy reserves it), not just the body, so an in-place upsize by timing-driven GPL (FIRM cells are
 # resized, not moved) cannot grow into a tapcell / foreign FIRM cell (KV io_ft kits_gen5 3_5 DPL-0033: 3 FIRM
 # INVx1 -> INVx3 over TAPCELLs). Default (unset) unchanged.
 set fw $w
 if {[info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "1"} {
  set fsp $sp; if {$fsp eq {}} { set fsp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> fsp }
  set fw [expr {max($w,int(ceil(double($w)/0.4*$fsp/$ff_sw))*$ff_sw)}]
 }
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
proc cland_ffkey {nm {rev 0}} {
 if {[regexp {^([^\[]*)\[([0-9]+)\\?\]\\?\[([0-9]+)\\?\](.*)$} $nm -> b s i t]} {
  if {$rev} { set i [expr {999999999-$i}] }
  return [format {%s|%09d|%09d|%s} [string trimright $b \\] $i $s $t]
 }
 return $nm
}
proc cland_place_ff {prefix rect tag} {
 global ff_blk ff_sw ff_dbu cland_done cland_ff_fill cland_cursor
 set ffs {};set comb 0;set need 0.0
 foreach i [$ff_blk getInsts] {
  set nm [$i getName]
  if {![regexp [format {(^|[/.])%s[/.]} $prefix] $nm]} continue
  if {[dict exists $cland_done $nm]} continue
  set m [$i getMaster]
  if {[$m isBlock]} { error "OT_CLAND unexpected macro in landing $nm" }
  if {![regexp {DFF|DHL|DLL|SDF} [$m getName]]} { incr comb;continue }
  lappend ffs [list [cland_ffkey $nm [string match {ring:*+ffr} $tag]] $i]
  set need [expr {$need+int(ceil(double([$m getWidth])/0.4/$ff_sw))*$ff_sw*double([$m getHeight])}]
 }
 if {![llength $ffs]} { return 0 }
 lassign $rect ax ay bx by
 set sp [expr {max(1.0,$cland_ff_fill*($bx-$ax)*($by-$ay)*$ff_dbu*$ff_dbu/$need)}]
 set cland_cursor {}
 foreach pr [lsort -dictionary -index 0 $ffs] { cland_put [lindex $pr 1] $rect $tag $sp 1 }
 set cland_cursor {}
 puts "OT_CLAND ring_place=ff $prefix: [llength $ffs] ring flops FIRM bit-major at spread [format %.4f $sp], $comb ring logic cells left to global placement"
 return [llength $ffs]
}
foreach spec $cland_groups {
 lassign $spec prefix rect tag
 set hit 0
 if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]} {
  if {![cland_place_ff $prefix $rect $tag]} { error "OT_CLAND no mapped ring flops found under $prefix" }
  continue
 }
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
