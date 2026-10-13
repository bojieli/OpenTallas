# Generated fixed legal strap-stage stations: no child/clock/pin budget change.
set sb [ord::get_db_block]
set su [[ord::get_db_tech] getDbUnitsPerMicron]
set sn 0
proc sr_init {} {
  set ::sr_rows {}; set ::sr_used [dict create]; set ::sr_fixed 0
  foreach r [$::sb getRows] {set rb [$r getBBox]; lassign [$r getOrigin] ox oy; set ::sr_sw [[$r getSite] getWidth]; set ::sr_rh [[$r getSite] getHeight]; lappend ::sr_rows [list $ox $oy [$rb xMax] [$r getOrient]]}
  foreach i [$::sb getInsts] {if {[$i isPlaced]} {set bb [$i getBBox]; sr_occupy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]}}
}
proc sr_occupy {x0 y0 x1 y1} {for {set k [expr {int(floor(double($y0)/$::sr_rh))}]} {$k <= int(floor(double($y1-1)/$::sr_rh))} {incr k} {dict lappend ::sr_used $k [list $x0 $x1]}}
proc sr_place {group cx cy} {
  set cx [expr {round($cx*$::su)}]; set cy [expr {round($cy*$::su)}]; set rows {}
  foreach r $::sr_rows {lassign $r ox oy xe ori; if {abs($oy-$cy) < 4*$::su} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}
  set rows [lsort -integer -index 0 $rows]
  foreach i [$group getInsts] {
    set w [[$i getMaster] getWidth]; set h [[$i getMaster] getHeight]; set found 0
    foreach r $rows {lassign $r delta ox oy xe ori; if {$oy < $cy-4*$::su || $oy+$h > $cy+4*$::su} continue
      set x [expr {$ox+int(ceil(double(max($ox,$cx-8*$::su)-$ox)/$::sr_sw))*$::sr_sw}]
      while {$x+$w <= min($xe,$cx+8*$::su)} {
        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {
          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}
        }
        if {$jump > $x} {set x $jump; continue}
        $i setOrient $ori; $i setLocation $x $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break
      }; if {$found} break
    }; if {!$found} {error "STRAP_REGION no legal station site for [$i getName]"}
  }
}
sr_init
proc sr_bind {net group} {
  for {set hop 0} {$hop < 5} {incr hop} {
    set driver {}; foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend driver $it}}
    if {[llength $driver] != 1} {error "STRAP_REGION ambiguous driver"}
    set si [[lindex $driver 0] getInst]; set master [[$si getMaster] getName]
    $group addInst $si
    if {[string match *DFF* $master]} {return 1}
    if {![regexp {^(INV|BUF)} $master]} {error "STRAP_REGION non-register logic $master"}
    set ins {}; foreach it [$si getITerms] {if {[$it isInputSignal]} {lappend ins [$it getNet]}}
    if {[llength $ins] != 1} {error "STRAP_REGION buffer input ambiguity"}; set net [lindex $ins 0]
  }; error "STRAP_REGION register not found"
}
set rg [odb::dbRegion_create $sb strap_l0_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$su)}] [expr {round(1236.8*$su)}] [expr {round(308*$su)}] [expr {round(1244.8*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s0]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s0: expected 26 DFFs, got $nc"}
sr_place $gr 300 1240.8
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l0_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(1096*$su)}] [expr {round(373*$su)}] [expr {round(1104*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s1]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s1: expected 26 DFFs, got $nc"}
sr_place $gr 365 1100
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l0_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(1056*$su)}] [expr {round(373*$su)}] [expr {round(1064*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s2]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s2: expected 26 DFFs, got $nc"}
sr_place $gr 365 1060
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l0_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$su)}] [expr {round(1056*$su)}] [expr {round(308*$su)}] [expr {round(1064*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s3]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s3: expected 26 DFFs, got $nc"}
sr_place $gr 300 1060
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l0_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$su)}] [expr {round(1029.68*$su)}] [expr {round(268*$su)}] [expr {round(1037.68*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s4]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s4: expected 26 DFFs, got $nc"}
sr_place $gr 260 1033.68
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l1_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(332*$su)}] [expr {round(1236.8*$su)}] [expr {round(348*$su)}] [expr {round(1244.8*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s0]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s0: expected 26 DFFs, got $nc"}
sr_place $gr 340 1240.8
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l1_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(946*$su)}] [expr {round(373*$su)}] [expr {round(954*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s1]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s1: expected 26 DFFs, got $nc"}
sr_place $gr 365 950
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l1_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(646*$su)}] [expr {round(373*$su)}] [expr {round(654*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s2]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s2: expected 26 DFFs, got $nc"}
sr_place $gr 365 650
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l1_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(346*$su)}] [expr {round(373*$su)}] [expr {round(354*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s3]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s3: expected 26 DFFs, got $nc"}
sr_place $gr 365 350
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $sb strap_l1_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$su)}] [expr {round(196.0*$su)}] [expr {round(268*$su)}] [expr {round(204.0*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s4]
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s4: expected 26 DFFs, got $nc"}
sr_place $gr 260 200.0
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
if {$sn != 260} {error "STRAP_REGION expected 260 DFFs"}
puts "STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed"
