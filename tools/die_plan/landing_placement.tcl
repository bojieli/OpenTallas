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
set cland_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc cland_put {i rect tag} {
 global ff_x0 ff_y0 ff_x1 ff_y1 ff_rh ff_sw ff_dbu ff_orient cland_occ cland_done cland_n cland_fh
 set name [$i getName]
 if {[dict exists $cland_done $name]} { error "OT_CLAND duplicate placement $name" }
 lassign $rect ax ay bx by
 set ax [expr {max($ff_x0,int(ceil($ax*$ff_dbu)))}];set ay [expr {max($ff_y0,int(ceil($ay*$ff_dbu)))}]
 set bx [expr {min($ff_x1,int(floor($bx*$ff_dbu)))}];set by [expr {min($ff_y1,int(floor($by*$ff_dbu)))}]
 set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
 set startx [expr {$ff_x0+int(ceil(double($ax-$ff_x0)/$ff_sw))*$ff_sw}]
 set starty [expr {$ff_y0+int(ceil(double($ay-$ff_y0)/$ff_rh))*$ff_rh}]
 for {set y $starty} {$y+$h<=$by} {incr y $ff_rh} {
  if {![dict exists $ff_orient $y]} continue
  set x $startx
  while {$x+$w<=$bx} {
   set skip $x;set r0 [expr {int(($y-$ff_y0)/$ff_rh)}];set r1 [expr {int(ceil(double($y+$h-$ff_y0)/$ff_rh))}]
   for {set r $r0} {$r<$r1} {incr r} {
    if {![dict exists $cland_occ $r]} continue
    foreach interval [dict get $cland_occ $r] {
     lassign $interval l u
     if {$x<$u && $x+$w>$l} { set skip [expr {max($skip,$u)}] }
    }
   }
   if {$skip>$x} { set x [expr {$ff_x0+int(ceil(double($skip-$ff_x0)/$ff_sw))*$ff_sw}];continue }
   if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED }
   $i setOrient [dict get $ff_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
   # Reserve spacing as well as the real body. Density margin permits the
   # datapath mux/control cells and leaves room for clock/reset repair.
   cland_occupy $x $y [expr {int(ceil(double($w)/0.4/$ff_sw))*$ff_sw}] $h
   dict set cland_done $name 1;incr cland_n
   puts $cland_fh "$name\tcland:$tag\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\t-"
   return
  }
 }
 error "OT_CLAND no legal nonoverlapping row/site in reserved band for $name ($tag)"
}
# Registered status outputs sit at their declared source point, separately
# from the ring storage band; the collector then follows its original tree.
foreach spec $cland_status {
 lassign $spec net x y
 set n [$ff_blk findNet $net]
 if {$n eq "NULL"} { error "OT_CLAND missing actual status net $net" }
 set drivers {}
 foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { lappend drivers [$it getInst] } }
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
foreach spec $cland_groups {
 lassign $spec prefix rect tag
 set hit 0
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
