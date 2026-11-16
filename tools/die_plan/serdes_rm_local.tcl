# Opt-in S81 RM locality helper: physical placement only; default off.
# Compose into a fresh reviewed capsule before DPL; never mutate an active kit. Existing FFs, data/reset/clock
# nets, phases and all reset release edges remain identical. F2 scope50 FFs:
# 17 actual rclk controls (including f2 alias fault) +rt_c +24rpq +8rt_d.
# Explicit physical profile OT_SERDES_RM_LOCAL_EMPTY8=1 adds8 existing rpw
# at g_rd[k].g_local.g_empty_local.rpw (RTL define OT_S81_SERDES_RM_LOCAL_EMPTY8).
# It requires58 existing FFs and69 bankregs, retains global rrst_nc reset.
# This extended selector is tested, not a fresh J ODB/CTS qualification.
namespace eval ot_rm_local {
 variable blk;variable dbu;variable selected;variable roots;variable cells
 variable xy;variable occupied;variable macs;variable core
 variable empty8 0
 proc clockpin {i} {
  foreach t [$i getITerms] {if {[[$t getMTerm] getName] in {CLK CLKN CK CKN}} {return $t}}
  return {}
 }
 proc canonical {n} {string map [list [format %c 92] {}] $n}
 proc coreclock {i} {
  set p [clockpin $i]
  expr {$p ne {} && [$p getNet] ne "NULL" && [regexp {^clk(?:_t[0-9]+)?$} [[$p getNet] getName]]}
 }
 proc bbox {i} {set z [$i getBBox];return [list [$z xMin] [$z yMin] [$z xMax] [$z yMax]]}
 proc centroid {items} {
  variable xy
  set x 0.;set y 0.
  dict for {n i} $items {lassign [dict get $xy $n] ix iy;set x [expr {$x+$ix}];set y [expr {$y+$iy}]}
  return [list [expr {$x/[dict size $items]}] [expr {$y/[dict size $items]}]]
 }
 proc wire {i} {regexp {^(BUF|INV|HB|CKBUF|CKINV)} [[$i getMaster] getName]}
 # Combinational feedback may move only when every sequential root is one of
 # the explicitly selected local-rclk FFs. Wclk state, memories and pads stop it.
 proc cone {net seen} {
  variable selected
  if {$net eq "NULL" || $net eq {} || [dict exists $seen [$net getName]]} {return [list 0 {}]}
  dict set seen [$net getName] 1;set drivers {}
  foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$t getInst]}}
  if {[llength $drivers]!=1} {return [list 0 {}]}
  set i [lindex $drivers 0];set n [$i getName];set m [$i getMaster]
  if {[dict exists $selected $n]} {return [list 1 {}]}
  if {[clockpin $i] ne {} || [$m isBlock]} {return [list 0 {}]}
  if {[string match TIE* [$m getName]]} {return [list 1 {}]}
  set out [dict create $n $i]
  foreach t [$i getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT" || [[$t getMTerm] getName] in {VDD VSS VPWR VGND}} continue
   lassign [cone [$t getNet] $seen] ok c
   if {!$ok} {return [list 0 {}]}
   set out [dict merge $out $c]
  }
  return [list 1 $out]
 }
 proc leaves {net seen} {
  if {$net eq "NULL" || $net eq {} || [dict exists $seen [$net getName]]} {return [list {} {} {}]}
  dict set seen [$net getName] 1;set buffers {};set sinks {};set other {}
  foreach t [$net getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   set i [$t getInst];set n [$i getName]
   if {[wire $i]} {
    dict set buffers $n $i
    foreach o [$i getITerms] {
     if {[[$o getMTerm] getIoType] ne "OUTPUT"} continue
     lassign [leaves [$o getNet] $seen] b s e
     set buffers [dict merge $buffers $b];set sinks [dict merge $sinks $s];set other [dict merge $other $e]
    }
   } elseif {[clockpin $i] ne {} && [[$t getMTerm] getName] in {RESETN SETN}} {
    dict set sinks $n $i
   } else {dict set other "$n/[[$t getMTerm] getName]" 1}
  }
  return [list $buffers $sinks $other]
 }
 proc overlap {a b} {lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1;expr {$x0<$u1 && $x1>$u0 && $y0<$v1 && $y1>$v0}}
 proc legal {r} {
  variable occupied;variable macs;variable core
  lassign $r x0 y0 x1 y1;lassign $core a b c d
  if {$x0<$a || $y0<$b || $x1>$c || $y1>$d} {return 0}
  foreach box $macs {if {[overlap $r $box]} {return 0}}
  # Coarse5um spatial hash, only querying bins crossed by this cell's bbox.
  variable dbu;set step [expr {5*$dbu}]
  for {set x [expr {int(floor($x0/$step))}]} {$x<=[expr {int(floor($x1/$step))}]} {incr x} {
   for {set y [expr {int(floor($y0/$step))}]} {$y<=[expr {int(floor($y1/$step))}]} {incr y} {
    if {![dict exists $occupied "$x,$y"]} continue
    foreach box [dict get $occupied "$x,$y"] {if {[overlap $r $box]} {return 0}}
   }
  }
  return 1
 }
 proc occupy {r} {
  variable occupied;variable dbu;set step [expr {5*$dbu}];lassign $r x0 y0 x1 y1
  for {set x [expr {int(floor($x0/$step))}]} {$x<=[expr {int(floor($x1/$step))}]} {incr x} {
   for {set y [expr {int(floor($y0/$step))}]} {$y<=[expr {int(floor($y1/$step))}]} {incr y} {dict lappend occupied "$x,$y" $r}
  }
 }
 proc site {i target} {
  variable dbu;variable xy
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_RM_LOCAL refuses fixed selected cell [$i getName]"}
  set m [$i getMaster];set w [$m getWidth];set h [$m getHeight]
  lassign $target ax ay
  set sx [expr {.054*$dbu}];set sy [expr {.27*$dbu}]
  set ax [expr {round($ax/$sx)*$sx}];set ay [expr {round($ay/$sy)*$sy}]
  # Find individual vacant sites; do not assume a whole empty rectangle exists.
  for {set radius 0} {$radius<=120} {incr radius} {
   set ys [expr {$radius*.27*$dbu}];set xs [expr {$radius*.54*$dbu}]
   foreach p [list [list $ax [expr {$ay+$ys}]] [list $ax [expr {$ay-$ys}]] [list [expr {$ax+$xs}] $ay] [list [expr {$ax-$xs}] $ay] [list [expr {$ax+$xs}] [expr {$ay+$ys}]] [list [expr {$ax-$xs}] [expr {$ay-$ys}]] [list [expr {$ax+$xs}] [expr {$ay-$ys}]] [list [expr {$ax-$xs}] [expr {$ay+$ys}]]] {
    lassign $p x y;set r [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
    if {![legal $r]} continue
    occupy $r;dict set xy [$i getName] [list $x $y]
    return [list $i $x $y]
   }
  }
  error "OT_RM_LOCAL no vacant macro/halo-safe site within65um of target for [$i getName]"
 }
 proc run {} {
  variable empty8
  set empty8 [expr {[info exists ::env(OT_SERDES_RM_LOCAL_EMPTY8)] && $::env(OT_SERDES_RM_LOCAL_EMPTY8) eq "1"}]
  variable blk;variable dbu;variable selected;variable roots;variable cells
  variable xy;variable occupied;variable macs;variable core
  set blk [ord::get_db_block];set dbu [expr {double([$blk getDbUnitsPerMicron])}]
  set ctrl {};set rtc {};set bankq {};set bankptr {};set bankwrap {};set bankrst {};set selected {};set xy {}
  foreach i [$blk getInsts] {
   set n [$i getName];lassign [$i getLocation] x y;dict set xy $n [list $x $y]
   if {![coreclock $i]} continue
   set cn [canonical $n]
   if {[regexp {u_core[.]g_rst_tree[.]rt_c[$/]} $cn]} {dict set rtc $n $i;dict set selected $n $i
   } elseif {[regexp {u_core[.]g_rst_tree[.]rt_d.([0-7]).} $cn -> k]} {dict set bankrst $k $n $i;dict set selected $n $i
   } elseif {[regexp {u_core[.]u_rm[.](rp|rp_g|wp_g1|wp_g2|f1|f2|fault)([^A-Za-z_0-9])} $cn]} {dict set ctrl $n $i;dict set selected $n $i
   } elseif {[regexp {u_core[.]u_rm[.]g_rd.([0-7]).[.]g_local[.]rpq} $cn -> k]} {dict set bankptr $k $n $i;dict set selected $n $i
   } elseif {$empty8 && [regexp {u_core[.]u_rm[.]g_rd.([0-7]).[.]g_local[.]g_empty_local[.]rpw} $cn -> k]} {dict set bankwrap $k $n $i;dict set selected $n $i
   } elseif {[regexp {u_core[.]u_rm[.]g_rd.([0-7]).[.]q} $cn -> k]} {dict set bankq $k $n $i}
  }
  set expected [expr {$empty8 ? 58 : 50}]
  if {[dict size $ctrl]!=17 || [dict size $rtc]!=1 || [dict size $selected]!=$expected} {error "OT_RM_LOCAL scope mismatch ctrl=[dict size $ctrl] rt_c=[dict size $rtc] FF=[dict size $selected], expected17/1/$expected (LOCAL_EMPTY8=$empty8)"}
  set global [dict merge $ctrl $rtc];set allq {};set targets {}
  for {set k 0} {$k<8} {incr k} {
   if {![dict exists $bankq $k] || ![dict exists $bankptr $k] || ![dict exists $bankrst $k] || [dict size [dict get $bankq $k]]!=64 || [dict size [dict get $bankptr $k]]!=3 || [dict size [dict get $bankrst $k]]!=1} {error "OT_RM_LOCAL bank$k must contain64q/3rpq/1rt_d"}
   if {$empty8 && (![dict exists $bankwrap $k] || [dict size [dict get $bankwrap $k]]!=1)} {error "OT_RM_LOCAL EMPTY8 bank$k must contain1 existing rpw"}
   set allq [dict merge $allq [dict get $bankq $k]]
   dict set targets $k [centroid [dict get $bankq $k]]
  }
  set center [centroid $allq];set cells $selected;set cones {};set usage {};set groups {}
  # First classify feedback cones, then keep gates shared by multiple banks global.
  dict for {n i} $selected {
   foreach pin [$i getITerms] {
    if {[[$pin getMTerm] getName] ne "D"} continue
    lassign [cone [$pin getNet] {}] ok c
    if {$ok} {dict set cones $n $c;set cells [dict merge $cells $c]}
   }
  }
  set resetbuf {}
  dict for {n i} [dict merge $rtc {*}[dict values $bankrst]] {
   foreach pin [$i getITerms] {
    if {[[$pin getMTerm] getIoType] ne "OUTPUT"} continue
    lassign [leaves [$pin getNet] {}] c sinks other
    if {[dict size $other]} {error "OT_RM_LOCAL reset output has unowned combinational consumers $n: [dict keys $other]"}
    dict for {sn si} $sinks {if {![dict exists $selected $sn] && ![dict exists $allq $sn]} {error "OT_RM_LOCAL reset output reaches unowned/wclk register $sn"}}
    set resetbuf [dict merge $resetbuf $c];set cells [dict merge $cells $c]
   }
  }
  dict for {n i} $ctrl {dict set groups $n global};dict for {n i} $rtc {dict set groups $n global}
  for {set k 0} {$k<8} {incr k} {
   set local [dict merge [dict get $bankptr $k] [dict get $bankrst $k]]
   if {$empty8} {set local [dict merge $local [dict get $bankwrap $k]]}
   dict for {n i} $local {dict set groups $n $k}
  }
  dict for {n c} $cones {
   set g [dict get $groups $n]
   dict for {cn ci} $c {dict set usage $cn $g 1}
  }
  dict for {n v} $usage {dict set groups $n [expr {[dict size $v]==1 ? [lindex [dict keys $v] 0] : "global"}]}
  set ca [$blk getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set occupied {};set macs {};set halo [expr {8.64*$dbu}]
  foreach i [$blk getInsts] {
   if {[[$i getMaster] isBlock]} {set r [bbox $i];lassign $r a b c d;lappend macs [list [expr {$a-$halo}] [expr {$b-$halo}] [expr {$c+$halo}] [expr {$d+$halo}]];continue}
   if {![dict exists $cells [$i getName]]} {occupy [bbox $i]}
  }
  set moves {}
  # FFs first so reset-buffer centroids use their proposed locations.
  dict for {n i} $selected {set g [dict get $groups $n];lappend moves [site $i [expr {$g eq "global" ? $center : [dict get $targets $g]}]]}
  dict for {n i} $cells {
   if {[dict exists $selected $n] || [dict exists $resetbuf $n]} continue
   set g [dict get $groups $n];lappend moves [site $i [expr {$g eq "global" ? $center : [dict get $targets $g]}]]
  }
  dict for {n i} $resetbuf {
   set s {};foreach pin [$i getITerms] {if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lassign [leaves [$pin getNet] {}] b l e;set s [dict merge $s $l]}}
   if {![dict size $s]} {error "OT_RM_LOCAL buffer has no reset leaves $n"}
   lappend moves [site $i [centroid $s]]
  }
  foreach v $moves {lassign $v i x y;$i setLocation [expr {int($x)}] [expr {int($y)}];$i setPlacementStatus PLACED}
  puts "OT_RM_LOCAL moved_existing_FF=$expected total_existing_cells=[llength $moves] ctrl=17 rt_c=1 rpq=24 rt_d=8 rpw=[expr {$empty8 ? 8 : 0}]; q512/wclk/fixedsites unchanged; target_um=[expr {[lindex $center 0]/$dbu}],[expr {[lindex $center 1]/$dbu}]"
  puts "OT_RM_LOCAL clock/reset/data identities unchanged; sourceearly-116/late0 and residual hold/removal repair remain; DPL orientation/legalization + actual image + STA pending"
 }
 # Call AFTER the candidate's own clock_taps assignment for complete load visibility.
 proc visibility {{root clk_t14}} {
  variable blk
  set blk [ord::get_db_block];set net [$blk findNet $root]
  if {$net eq "NULL"} {error "OT_RM_LOCAL no clock root $root"}
  set todo [list $net];set seen {};set rm {};set other {};set unknown {}
  while {[llength $todo]} {
   set net [lindex $todo 0];set todo [lrange $todo 1 end]
   if {[dict exists $seen [$net getName]]} continue;dict set seen [$net getName] 1
   foreach t [$net getITerms] {
    if {[[$t getMTerm] getIoType] ne "INPUT"} continue
    set i [$t getInst];set n [$i getName]
    if {[wire $i]} {foreach q [$i getITerms] {if {[[$q getMTerm] getIoType] eq "OUTPUT"} {lappend todo [$q getNet]}};continue}
    if {[[$t getMTerm] getName] ni {CLK CLKN CK CKN}} {dict set unknown "$n/[[$t getMTerm] getName]" 1;continue}
    if {[regexp {u_core[.](u_rm[.]|g_rst_tree[.]rt_[cd])} [canonical $n]]} {dict set rm $n 1} else {dict set other $n 1}
   }
  }
  puts "OT_RM_LOCAL ROOT_VISIBILITY $root RM=[dict size $rm] nonRM=[dict size $other] unknown=[dict size $unknown] nonRM_names=[dict keys $other] unknown_names=[dict keys $unknown]"
  return [list $rm $other $unknown]
 }
}
if {[info exists ::env(OT_SERDES_RM_LOCAL)] && $::env(OT_SERDES_RM_LOCAL) eq "1"} {ot_rm_local::run}
