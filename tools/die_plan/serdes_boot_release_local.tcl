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


# Apply only to the unchanged t13 outline with a legal north pocket and the
# modelled PMA-pair Y-27 translation. M6/M7 carry reset; M8 stays clock/PG.
proc ot_serdes_boot_release_local {} {
 set b [ord::get_db_block];set d [expr {double([$b getDbUnitsPerMicron])}]
 set ff {};set target {{1656.72 905.85} {1450.008 750.06} {1235.034 625.05}}
 foreach i [$b getInsts] {
  if {[regexp {u_boot_release[.]g_stage\\?\[([0-2])\\?\][.]rq} [$i getName] -> k] && [string match DFF* [[$i getMaster] getName]]} {
   if {[dict exists $ff $k]} {error "OT_BOOT_RELEASE duplicate stage $k"}
   dict set ff $k $i
  }
 }
 if {[dict size $ff]!=3} {error "OT_BOOT_RELEASE expected3 kept stages, found [dict size $ff]"}
 set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
 set macs {};set halo [expr {8.64*$d}]
 foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set z [$i getBBox];lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]
 }
 set moves {}
 for {set k 0} {$k<3} {incr k} {
  set i [dict get $ff $k];lassign [lindex $target $k] x y
  set x [expr {round($x/0.054)*0.054*$d}];set y [expr {round($y/0.27)*0.27*$d}]
  set m [$i getMaster];set r [list $x $y [expr {$x+[$m getWidth]}] [expr {$y+[$m getHeight]}]]
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
 if {[llength $tails]!=4 || $max_tail>405.0} {error "OT_BOOT_RELEASE native sync scope/tail mismatch count=[llength $tails] max_um=$max_tail"}
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
 puts "OT_BOOT_RELEASE placed3 kept RCK release stages; model hops316/363/340um; actual native tails_um=$tails max_um=$max_tail; original FIRM authority preserved"
}
if {[info exists ::env(OT_SERDES_BOOT_RELEASE_LOCAL)] && $::env(OT_SERDES_BOOT_RELEASE_LOCAL) eq "1"} {ot_serdes_boot_release_local}
