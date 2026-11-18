# Anchor-aware SerDes reset authority placement for sized BOOT_RELEASE3; default off.
# Preserve every FIRM boundary site and all nets/stages/clocks. A PMA-free north
# strip must exist first; refuse an authority anchor inside a macro halo.
namespace eval ot_reset_anchor {
 variable regs;variable blk
 proc fanin {net seen} {
  variable regs
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} {return [list 0 {}]}
  dict set seen [$net getName] 1
  set drivers {}
  foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$t getInst]}}
  if {[llength $drivers]!=1} {return [list 0 {}]}
  set i [lindex $drivers 0];set n [$i getName];set m [$i getMaster]
  if {[dict exists $regs $n]} {return [list 1 {}]}
  if {[$m isBlock] || [$m isSequential]} {return [list 0 {}]}
  set cells {}
  # Do not drag a shared constant driver away from unrelated clients.
  if {![string match TIE* [$m getName]] || [llength [$net getITerms]]<=16} {dict set cells $n $i}
  foreach t [$i getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT" || [[$t getMTerm] getName] in {VDD VSS}} continue
   set nn [$t getNet]
   if {$nn ne "NULL" && [$nn getSigType] in {POWER GROUND CLOCK}} continue
   lassign [fanin $nn $seen] ok c
   if {!$ok} {return [list 0 {}]}
   set cells [dict merge $cells $c]
  }
  return [list 1 $cells]
 }
 proc free {rect macros core} {
  lassign $rect x0 y0 x1 y1;lassign $core a b c d
  if {$x0<$a || $y0<$b || $x1>$c || $y1>$d} {return 0}
  foreach r $macros {lassign $r a b c d;if {$x0<$c && $x1>$a && $y0<$d && $y1>$b} {return 0}}
  return 1
 }
 proc delivery {net seen} {
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} {return {}}
  dict set seen [$net getName] 1;set out {}
  foreach t [$net getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   set i [$t getInst];set m [$i getMaster]
   if {[regexp {^(BUF|INV|HB|CKBUF|CKINV)} [$m getName]]} {
    foreach o [$i getITerms] {if {[[$o getMTerm] getIoType] eq "OUTPUT"} {set out [dict merge $out [delivery [$o getNet] $seen]]}}
   } else {dict set out [$i getName] $i}
  }
  return $out
 }
 proc run {} {
  variable regs;variable blk
  set blk [ord::get_db_block];set dbu [expr {double([$blk getDbUnitsPerMicron])}]
  set regs {};set cells {};set anchors {}
  foreach i [$blk getInsts] {
   set n [$i getName]
   if {[string first {g_locksafe.u_hold.} $n]>=0 && [string match DFF* [[$i getMaster] getName]]} {dict set regs $n $i}
  }
  if {![dict size $regs]} {error "OT_RESET_ANCHOR no authority registers"}
  set cells $regs
  dict for {n i} $regs {
   foreach t [$i getITerms] {
    if {[[$t getMTerm] getName] ni {D RESETN SETN}} continue
    lassign [fanin [$t getNet] {}] ok c
    if {$ok} {set cells [dict merge $cells $c]}
   }
  }
  set out {}
  foreach net [$blk getNets] {
   if {[regexp {(g_locksafe[.]u_hold[.]core_rst_n|g_locksafe[.]u_boot_release[.]rst_n|u_core[.]rst_g_authority)$} [$net getName]]} {set out $net;break}
  }
  if {$out eq {}} {error "OT_RESET_ANCHOR authority output not found"}
  lassign [fanin $out {}] ok c
  if {!$ok} {error "OT_RESET_ANCHOR output has an external combinational authority"}
  set cells [dict merge $cells $c]
  dict for {n i} $cells {
   if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {dict set anchors $n $i}
  }
  if {![dict size $anchors]} {error "OT_RESET_ANCHOR no immutable boundary anchor"}
  set ca [$blk getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set macros {};set halo [expr {8.64*$dbu}]
  foreach i [$blk getInsts] {
   if {![[$i getMaster] isBlock]} continue
   set z [$i getBBox]
   lappend macros [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]
  }
  set ax 0.;set ay 0.
  dict for {n i} $anchors {
   set z [$i getBBox];set r [list [$z xMin] [$z yMin] [$z xMax] [$z yMax]]
   if {![free $r $macros $core]} {error "OT_RESET_ANCHOR immutable boundary site intersects macro/halo or core edge: $n"}
   lassign [$i getLocation] x y;set ax [expr {$ax+$x}];set ay [expr {$ay+$y}]
  }
  set ax [expr {$ax/[dict size $anchors]}];set ay [expr {$ay/[dict size $anchors]}]
  set side [expr {int(ceil(sqrt([dict size $cells]-[dict size $anchors])))}]
  set pitch [expr {1.08*$dbu}];set w [expr {($side+2)*$pitch}]
  set chosen {}
  # Prefer immediately below the north boundary anchor. Search only <=100um.
  for {set d 0} {$d<=100 && ![llength $chosen]} {incr d 5} {
   foreach dx [list 0 $d [expr {-$d}]] {
    foreach dy [list [expr {-$d}] $d 0] {
     set x0 [expr {$ax-$w/2+$dx*$dbu}];set y1 [expr {$ay-0.81*$dbu+$dy*$dbu}]
     set r [list $x0 [expr {$y1-$w}] [expr {$x0+$w}] $y1]
     if {[free $r $macros $core]} {set chosen $r;break}
    }
    if {[llength $chosen]} break
   }
  }
  if {![llength $chosen]} {error "OT_RESET_ANCHOR no macro-free pocket within100um"}
  lassign $chosen x0 y0 x1 y1
  set k 0;set area 0.
  dict for {n i} $cells {
   if {[dict exists $anchors $n]} continue
   set x [expr {$x0+(1+$k%$side)*$pitch}];set y [expr {$y0+(1+$k/$side)*$pitch}]
   $i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED
   set m [$i getMaster];set area [expr {$area+[$m getWidth]*[$m getHeight]/($dbu*$dbu)}]
   incr k
  }
  set driver {}
  foreach t [$out getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {set driver [$t getInst]}}
  set maxspan 0.;set sinks {}
  lassign [$driver getLocation] x y
  dict for {n i} [delivery $out {}] {
   lassign [$i getLocation] tx ty
   set span [expr {(abs($tx-$x)+abs($ty-$y))/$dbu}]
   if {$span>$maxspan} {set maxspan $span}
   lappend sinks [list $n $span]
  }
  puts "OT_RESET_ANCHOR moved $k authority-only cells area_um2 $area; preserved [dict size $anchors] FIRM anchors; pocket_um [expr {$x0/$dbu}] [expr {$y0/$dbu}] [expr {$x1/$dbu}] [expr {$y1/$dbu}]"
  puts "OT_RESET_ANCHOR delivery_max_um $maxspan sinks $sinks"
 }
}


# S81-SERDES-GEN 11-17: the three stage sites are DERIVED from the DB (ot_serdes_boot_sites), not t13 constants: evenly along the
# Manhattan path from the FIRM authority anchor (g_locksafe.u_hold DFF) to the centroid of the u_core.rs_[rt] sync FFs, each hop
# <= 405 um.  Gen env OT_BOOT_RELEASE_SITES="x,y;x,y;x,y" (um; plan key serdes_boot_release_sites) wins.  A site on a macro/halo
# goes to the nearest free site within 100 um.  M6/M7 carry reset; M8 stays clock/PG.
# Yosys preserves final rq as a net alias but may name its physical DFF
# released_n. Select the exact kept stage identity, never arbitrary rq nets.
proc ot_serdes_boot_release_registers {b} {
 set ff {}
 foreach i [$b getInsts] {
  if {![string match DFF* [[$i getMaster] getName]]} continue
  set k {}
  if {[regexp {u_boot_release[.]g_stage\\?\[([0-2])\\?\][.]rq} [$i getName] -> k]} {
  } elseif {[regexp {u_boot_release[.]released_n(?:[$]|$)} [$i getName]]} {set k 2}
  if {$k eq {}} continue
  if {[dict exists $ff $k]} {error "OT_BOOT_RELEASE duplicate stage $k"}
  dict set ff $k $i
 }
 if {[dict size $ff]!=3} {error "OT_BOOT_RELEASE expected3 kept stages, found [dict size $ff]"}
 return $ff
}

# Reach by fixed script (11-17): pull each native sync tail DFF farther than 405 um (Manhattan) from the stage-2 site
# (tx,ty um) along its line to stage 2 until its span is <= 380 um (then 360 .. 260) on a macro/halo-free core site.
# The DFF stays PLACED (DPL legalises); nets, stages and clocks are unchanged.  Returns {name old_span new_span} rows.
proc ot_serdes_boot_tail_pull {b d tails tx ty macs core} {
 set pulled {}
 foreach tl $tails {
  lassign $tl tn span
  if {$span<=405.0} continue
  set i [$b findInst $tn];lassign [$i getLocation] x y
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_BOOT_RELEASE fixed tail $tn span $span cannot move"}
  set m [$i getMaster];set ok 0
  foreach goal {380.0 360.0 340.0 320.0 300.0 280.0 260.0} {
   set f [expr {($span-$goal)/$span}]
   set nx [expr {$x+($tx*$d-$x)*$f}];set ny [expr {$y+($ty*$d-$y)*$f}]
   set nx [expr {round($nx/$d/0.054)*0.054*$d}];set ny [expr {round($ny/$d/0.27)*0.27*$d}]
   set r [list $nx $ny [expr {$nx+[$m getWidth]}] [expr {$ny+[$m getHeight]}]]
   if {[ot_reset_anchor::free $r $macs $core]} {set ok 1;break}
  }
  if {!$ok} {error "OT_BOOT_RELEASE tail $tn span $span: no macro-free pull site"}
  $i setLocation [expr {int($nx)}] [expr {int($ny)}];$i setPlacementStatus PLACED
  lappend pulled [list $tn $span [expr {abs($nx/$d-$tx)+abs($ny/$d-$ty)}]]
 }
 return $pulled
}
# Optional placement-only BOOT pipeline data-path localization. Source/sink FFs,
# all nets and clock pins stay untouched. Only private BUF/INV chains move.
proc ot_serdes_boot_private_chain {src dst} {
 set pins {}
 foreach t [$dst getITerms] {if {[[$t getMTerm] getName] eq "RESETN"} {lappend pins $t}}
 if {[llength $pins]!=1} {error "OT_BOOT_PATH expected one RESETN on [$dst getName]"}
 set pin [lindex $pins 0];set seen {};set chain {}
 while {1} {
  set net [$pin getNet]
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} {error "OT_BOOT_PATH absent/cyclic reset path"}
  dict set seen [$net getName] 1
  set drivers {};set sinks {}
  foreach t [$net getITerms] {
   if {[$t isOutputSignal]} {lappend drivers $t}
   if {[$t isInputSignal]} {lappend sinks $t}
  }
  if {[llength $drivers]!=1 || [llength [$net getBTerms]]} {error "OT_BOOT_PATH external/multiple driver"}
  set drv [[lindex $drivers 0] getInst]
  if {$drv eq $src} {return [lreverse $chain]}
  set m [$drv getMaster]
  if {![regexp {^(BUF|INV)} [$m getName]] || [$m isBlock] || [$m isSequential]} {error "OT_BOOT_PATH non-buffer private path at [$drv getName]"}
  if {[llength $sinks]!=1 || [lindex $sinks 0] ne $pin} {error "OT_BOOT_PATH shared control at [$drv getName]"}
  if {[$drv getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_BOOT_PATH fixed cell [$drv getName]"}
  set ins {}
  foreach t [$drv getITerms] {if {[$t isInputSignal] && [$t getNet] ne "NULL"} {lappend ins $t}}
  if {[llength $ins]!=1} {error "OT_BOOT_PATH ambiguous input at [$drv getName]"}
  lappend chain $drv;set pin [lindex $ins 0]
 }
}
proc ot_serdes_boot_path_plan {ff d macs core} {
 set plans {};set summaries {}
 for {set k 0} {$k<2} {incr k} {
  set src [dict get $ff $k];set dst [dict get $ff [expr {$k+1}]]
  set chain [ot_serdes_boot_private_chain $src $dst]
  lassign [$src getLocation] sx sy;lassign [$dst getLocation] tx ty
  set prev [list $sx $sy];set before 0.;set after 0.;set maxhop 0.;set next {}
  set j 0;set n [llength $chain]
  foreach i $chain {
   incr j;lassign [$i getLocation] ox oy;lassign $prev px py
   set before [expr {$before+abs($ox-$px)+abs($oy-$py)}];set prev [list $ox $oy]
   set bx [expr {$sx+($tx-$sx)*double($j)/($n+1)}];set by [expr {$sy+($ty-$sy)*double($j)/($n+1)}]
   set found 0;set m [$i getMaster]
   foreach dy {0 5 -5 10 -10 20 -20} {
    foreach dx {0 5 -5 10 -10 20 -20} {
     set x [expr {round(($bx/$d+$dx)/0.054)*0.054*$d}];set y [expr {round(($by/$d+$dy)/0.27)*0.27*$d}]
     set r [list $x $y [expr {$x+[$m getWidth]}] [expr {$y+[$m getHeight]}]]
     if {[ot_reset_anchor::free $r $macs $core]} {set found 1;break}
    }
    if {$found} break
   }
   if {!$found} {error "OT_BOOT_PATH no macro-free path site [$i getName]"}
   lappend next [list $i [expr {int($x)}] [expr {int($y)}]]
  }
  lassign $prev px py;set before [expr {($before+abs($tx-$px)+abs($ty-$py))/$d}]
  set prev [list $sx $sy]
  foreach v [concat $next [list [list $dst $tx $ty]]] {
   lassign $v i x y;lassign $prev px py
   set hop [expr {(abs($x-$px)+abs($y-$py))/$d}];set after [expr {$after+$hop}]
   if {$hop>$maxhop} {set maxhop $hop};set prev [list $x $y]
  }
  if {$maxhop>405} {error "OT_BOOT_PATH new path hop $maxhop exceeds405"}
  set plans [concat $plans $next]
  lappend summaries [list $k [expr {$k+1}] cells $n before_um $before after_um $after maxhop_um $maxhop]
 }
 return [list $plans $summaries]
}
proc ot_serdes_boot_path_local {b d ff macs core} {
 lassign [ot_serdes_boot_path_plan $ff $d $macs $core] plans summaries
 # All graph, ownership and geometry checks complete before any mutation.
 foreach v $plans {lassign $v i x y;$i setLocation $x $y;$i setPlacementStatus PLACED}
 puts "OT_BOOT_PATH private_data_only [llength $plans] cells; $summaries; zero_added_cells_cycles; FF/clock/nets unchanged"
}

proc ot_serdes_boot_sites {b d} {
 if {[info exists ::env(OT_BOOT_RELEASE_SITES)] && $::env(OT_BOOT_RELEASE_SITES) ne ""} {
  set t {}
  foreach s [split $::env(OT_BOOT_RELEASE_SITES) ";"] {lassign [split $s ","] x y;lappend t [list $x $y]}
  if {[llength $t]!=3} {error "OT_BOOT_RELEASE OT_BOOT_RELEASE_SITES needs 3 x,y sites"}
  return $t
 }
 set an {};set an0 {};set sy {}
 foreach i [$b getInsts] {
  set n [$i getName]
  if {![string match DFF* [[$i getMaster] getName]]} continue
  if {[string first {g_locksafe.u_hold.} $n]>=0 && [$i getPlacementStatus] in {FIRM LOCKED COVER}} {
   lappend an0 [$i getLocation]
   # the boundary authority anchor of the boot transport step (serdes_boot_transport_local.tcl): lock_sync[1]
   if {[regexp {g_locksafe[.]u_hold[.]lock_sync.*1.*DFF} $n]} {lappend an [$i getLocation]}
  }
  if {[regexp {u_core[.]rs_[rt]\\?\[} $n]} {lappend sy [$i getLocation]}
 }
 if {![llength $an]} {set an $an0}
 if {![llength $an] || ![llength $sy]} {error "OT_BOOT_RELEASE cannot derive sites: [llength $an] FIRM authority anchors, [llength $sy] sync FFs"}
 set ax 0.;set ay 0.;foreach p $an {set ax [expr {$ax+[lindex $p 0]/double([llength $an])/$d}];set ay [expr {$ay+[lindex $p 1]/double([llength $an])/$d}]}
 set sx 0.;set sY 0.;foreach p $sy {set sx [expr {$sx+[lindex $p 0]/double([llength $sy])/$d}];set sY [expr {$sY+[lindex $p 1]/double([llength $sy])/$d}]}
 set hop [expr {(abs($sx-$ax)+abs($sY-$ay))/4.0}]
 if {$hop>405.0} {error "OT_BOOT_RELEASE derived hop $hop um exceeds 405 (anchor $ax,$ay sync $sx,$sY)"}
 set t {}
 for {set k 1} {$k<=3} {incr k} {lappend t [list [expr {$ax+($sx-$ax)*$k/4.0}] [expr {$ay+($sY-$ay)*$k/4.0}]]}
 puts "OT_BOOT_RELEASE derived sites $t hop_um $hop anchor $ax,$ay sync_centroid $sx,$sY"
 return $t
}

proc ot_serdes_boot_free_site {x y m macs core d} {
 for {set rad 0} {$rad<=100} {set rad [expr {$rad+2.16}]} {
  foreach dx [list 0 $rad [expr {-$rad}]] {
   foreach dy [list 0 $rad [expr {-$rad}]] {
    set px [expr {round(($x+$dx)/0.054)*0.054*$d}];set py [expr {round(($y+$dy)/0.27)*0.27*$d}]
    if {[ot_reset_anchor::free [list $px $py [expr {$px+[$m getWidth]}] [expr {$py+[$m getHeight]}]] $macs $core]} {return [list $px $py]}
   }
  }
 }
 return {}
}

proc ot_serdes_boot_release_local {} {
 set b [ord::get_db_block];set d [expr {double([$b getDbUnitsPerMicron])}]
 set ff [ot_serdes_boot_release_registers $b]
 set target [ot_serdes_boot_sites $b $d]
 set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
 set macs {};set halo [expr {8.64*$d}]
 foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set z [$i getBBox];lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]
 }
 set moves {}
 for {set k 0} {$k<3} {incr k} {
  set i [dict get $ff $k];lassign [lindex $target $k] x y
  set m [$i getMaster]
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {
   set x [expr {round($x/0.054)*0.054*$d}];set y [expr {round($y/0.27)*0.27*$d}]
  } else {
   set fs [ot_serdes_boot_free_site $x $y $m $macs $core $d]
   if {![llength $fs]} {error "OT_BOOT_RELEASE stage$k no macro/halo/core-free site within 100um of target"}
   lassign $fs x y
  }
  set r [list $x $y [expr {$x+[$m getWidth]}] [expr {$y+[$m getHeight]}]]
  if {![ot_reset_anchor::free $r $macs $core]} {error "OT_BOOT_RELEASE stage$k target intersects macro/halo/core"}
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {
   lassign [$i getLocation] ox oy
   if {abs($ox-$x)>1 || abs($oy-$y)>1} {error "OT_BOOT_RELEASE existing fixed stage$k cannot move"}
  }
  lappend moves [list $i $x $y]
 }
 set tails {};set max_tail 0.0
 lassign [lindex $target 2] tx ty
 foreach i [$b getInsts] {
  if {![regexp {u_core[.]rs_[rt]\\?\[} [$i getName]] || ![string match DFF* [[$i getMaster] getName]]} continue
  lassign [$i getLocation] x y;set span [expr {abs($x/$d-$tx)+abs($y/$d-$ty)}]
  lappend tails [list [$i getName] $span]
  if {$span>$max_tail} {set max_tail $span}
 }
 if {[llength $tails]!=4} {error "OT_BOOT_RELEASE native sync scope/tail mismatch count=[llength $tails] max_um=$max_tail"}
 # S81-SERDES-R2 H5 / FABLE-FIX-S81-SERDES (11-17): with a spread placement (PLACE_DENSITY 0.30) a native sync tail can land >405 um
 # from the fixed stage-2 site.  Reach by fixed script: pull each such tail DFF along its line to stage 2 until its
 # Manhattan span is <=380 um, on a macro/halo-free core site (PLACED; DPL legalises).  Same nets/stages/clocks.
 if {$max_tail>405.0} {
  set pulled [ot_serdes_boot_tail_pull $b $d $tails $tx $ty $macs $core]
  set tails {};set max_tail 0.0
  foreach i [$b getInsts] {
   if {![regexp {u_core[.]rs_[rt]\\?\[} [$i getName]] || ![string match DFF* [[$i getMaster] getName]]} continue
   lassign [$i getLocation] x y;set span [expr {abs($x/$d-$tx)+abs($y/$d-$ty)}]
   lappend tails [list [$i getName] $span]
   if {$span>$max_tail} {set max_tail $span}
  }
  puts "OT_BOOT_RELEASE tail pull: $pulled"
  if {[llength $tails]!=4 || $max_tail>405.0} {error "OT_BOOT_RELEASE tail pull left count=[llength $tails] max_um=$max_tail"}
 }
 # Validate the three new sites before changing either authority or relays.
 ot_reset_anchor::run
 # These are new soft pipeline sites, not boundary authorities. Leave them
 # PLACED so DPL can choose legal row orientation and resolve local occupancy.
 # Any pre-existing fixed stage was checked above and remains untouched.
 foreach v $moves {
  lassign $v i x y
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  $i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED
 }
 if {[info exists ::env(OT_SERDES_BOOT_PATH_LOCAL)] && $::env(OT_SERDES_BOOT_PATH_LOCAL) eq "1"} {ot_serdes_boot_path_local $b $d $ff $macs $core}
 puts "OT_BOOT_RELEASE placed3 kept RCK release stages; model hops316/363/340um; actual native tails_um=$tails max_um=$max_tail; original FIRM authority preserved"
}
if {[info exists ::env(OT_SERDES_BOOT_RELEASE_LOCAL)] && $::env(OT_SERDES_BOOT_RELEASE_LOCAL) eq "1"} {ot_serdes_boot_release_local}
