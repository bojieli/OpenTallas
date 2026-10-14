# Generated fixed legal strap-stage stations: no child/clock/pin budget change.
set ::sr_blk [ord::get_db_block]
set ::sr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set sn 0
proc sr_init {} {
  set ::sr_rows {}; set ::sr_used [dict create]; set ::sr_fixed 0
  foreach r [$::sr_blk getRows] {set rb [$r getBBox]; lassign [$r getOrigin] ox oy; set ::sr_sw [[$r getSite] getWidth]; set ::sr_rh [[$r getSite] getHeight]; lappend ::sr_rows [list $ox $oy [$rb xMax] [$r getOrient]]}
  set ::sr_mw_inv 0; set ::sr_mw_dff 0
  foreach lib [[ord::get_db] getLibs] {foreach m [$lib getMasters] {set n [$m getName]; if {[regexp {^INV} $n]} {set ::sr_mw_inv [expr {max($::sr_mw_inv,[$m getWidth])}]} elseif {[regexp {^DFF} $n]} {set ::sr_mw_dff [expr {max($::sr_mw_dff,[$m getWidth])}]}}}
  puts "STRAP_GROWTH_RESERVE INV $::sr_mw_inv DFF $::sr_mw_dff DBU $::sr_dbu"
  foreach i [$::sr_blk getInsts] {if {[$i isPlaced]} {set bb [$i getBBox]; sr_occupy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]}}
}
proc sr_occupy {x0 y0 x1 y1} {for {set k [expr {int(floor(double($y0)/$::sr_rh))}]} {$k <= int(floor(double($y1-1)/$::sr_rh))} {incr k} {dict lappend ::sr_used $k [list $x0 $x1]}}
proc sr_place {group cx cy} {
  set cx [expr {round($cx*$::sr_dbu)}]; set cy [expr {round($cy*$::sr_dbu)}]; set rows {}
  foreach r $::sr_rows {lassign $r ox oy xe ori; if {abs($oy-$cy) < 4*$::sr_dbu} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}
  set rows [lsort -integer -index 0 $rows]
  foreach i [$group getInsts] {
    set w [[$i getMaster] getWidth]; set h [[$i getMaster] getHeight]; set master [[$i getMaster] getName]; set mw [expr {[regexp {^INV} $master] ? $::sr_mw_inv : $::sr_mw_dff}]; set w [expr {max($w,$mw)+4*$::sr_sw}]; set found 0
    foreach r $rows {lassign $r delta ox oy xe ori; if {$oy < $cy-4*$::sr_dbu || $oy+$h > $cy+4*$::sr_dbu} continue
      set x [expr {$ox+int(ceil(double(max($ox,$cx-8*$::sr_dbu)-$ox)/$::sr_sw))*$::sr_sw}]
      while {$x+$w <= min($xe,$cx+8*$::sr_dbu)} {
        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {
          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}
        }
        if {$jump > $x} {set x $jump; continue}
        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break
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
set rg [odb::dbRegion_create $::sr_blk strap_l0_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$::sr_dbu)}] [expr {round(1236.8*$::sr_dbu)}] [expr {round(308*$::sr_dbu)}] [expr {round(1244.8*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s0: expected 26 DFFs, got $nc"}
sr_place $gr 300 1240.8
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$::sr_dbu)}] [expr {round(1096*$::sr_dbu)}] [expr {round(373*$::sr_dbu)}] [expr {round(1104*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s1: expected 26 DFFs, got $nc"}
sr_place $gr 365 1100
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$::sr_dbu)}] [expr {round(1056*$::sr_dbu)}] [expr {round(373*$::sr_dbu)}] [expr {round(1064*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s2: expected 26 DFFs, got $nc"}
sr_place $gr 365 1060
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$::sr_dbu)}] [expr {round(1056*$::sr_dbu)}] [expr {round(308*$::sr_dbu)}] [expr {round(1064*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s3: expected 26 DFFs, got $nc"}
sr_place $gr 300 1060
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$::sr_dbu)}] [expr {round(1029.68*$::sr_dbu)}] [expr {round(268*$::sr_dbu)}] [expr {round(1037.68*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s4]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s4: expected 26 DFFs, got $nc"}
sr_place $gr 260 1033.68
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(332*$::sr_dbu)}] [expr {round(1236.8*$::sr_dbu)}] [expr {round(348*$::sr_dbu)}] [expr {round(1244.8*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s0: expected 26 DFFs, got $nc"}
sr_place $gr 340 1240.8
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$::sr_dbu)}] [expr {round(946*$::sr_dbu)}] [expr {round(373*$::sr_dbu)}] [expr {round(954*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s1: expected 26 DFFs, got $nc"}
sr_place $gr 365 950
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$::sr_dbu)}] [expr {round(646*$::sr_dbu)}] [expr {round(373*$::sr_dbu)}] [expr {round(654*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s2: expected 26 DFFs, got $nc"}
sr_place $gr 365 650
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$::sr_dbu)}] [expr {round(346*$::sr_dbu)}] [expr {round(373*$::sr_dbu)}] [expr {round(354*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s3: expected 26 DFFs, got $nc"}
sr_place $gr 365 350
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$::sr_dbu)}] [expr {round(196.0*$::sr_dbu)}] [expr {round(268*$::sr_dbu)}] [expr {round(204.0*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s4]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s4: expected 26 DFFs, got $nc"}
sr_place $gr 260 200.0
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
if {$sn != 260} {error "STRAP_REGION expected 260 DFFs"}
puts "STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed"
set rn 0
set rg [odb::dbRegion_create $::sr_blk rst_p0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1234.8*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1242.8*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_p0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.p0$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_p0: expected 1 register, got $nc"}
sr_place $gr 376.8 1238.8
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1196*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1204*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n1$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n1: expected 1 register, got $nc"}
sr_place $gr 376.8 1200
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1156*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1164*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n2: expected 1 register, got $nc"}
sr_place $gr 376.8 1160
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1036*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1044*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n3: expected 1 register, got $nc"}
sr_place $gr 376.8 1040
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gn]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1018*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1026*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gn]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gn$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gn: expected 1 register, got $nc"}
sr_place $gr 376.8 1022
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_lhn]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(1010*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(1018*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_lhn]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_lhn$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_lhn: expected 1 register, got $nc"}
sr_place $gr 376.8 1014
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_t1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(896*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(904*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_t1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.t1$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_t1: expected 1 register, got $nc"}
sr_place $gr 376.8 900
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_m2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(756*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(764*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_m2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.m2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_m2: expected 1 register, got $nc"}
sr_place $gr 376.8 760
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_m3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(628*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(636*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_m3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.m3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_m3: expected 1 register, got $nc"}
sr_place $gr 376.8 632
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gm]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(614*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(622*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gm]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gm$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gm: expected 1 register, got $nc"}
sr_place $gr 376.8 618
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_ptw]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(606*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(614*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_ptw]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_ptw$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_ptw: expected 1 register, got $nc"}
sr_place $gr 376.8 610
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_pte]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(598*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(606*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_pte]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_pte$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_pte: expected 1 register, got $nc"}
sr_place $gr 376.8 602
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_t2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(556*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(564*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_t2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.t2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_t2: expected 1 register, got $nc"}
sr_place $gr 376.8 560
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(246*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(254*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.s3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_s3: expected 1 register, got $nc"}
sr_place $gr 376.8 250
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gs]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(228*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(236*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gs]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gs$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gs: expected 1 register, got $nc"}
sr_place $gr 376.8 232
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_lhs]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(368.8*$::sr_dbu)}] [expr {round(220*$::sr_dbu)}] [expr {round(384.8*$::sr_dbu)}] [expr {round(228*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_lhs]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_lhs$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_lhs: expected 1 register, got $nc"}
sr_place $gr 376.8 224
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
if {$rn != 16} {error "RESET_STATION expected 16 registers"}
puts "RESET_STATION_PLACED 16 FIXED_CELLS $::sr_fixed"
