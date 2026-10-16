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
odb::dbBox_create $rg [expr {round(92*$::sr_dbu)}] [expr {round(1176.32*$::sr_dbu)}] [expr {round(108*$::sr_dbu)}] [expr {round(1184.32*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s0: expected 26 DFFs, got $nc"}
sr_place $gr 100 1180.32
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(52*$::sr_dbu)}] [expr {round(1146*$::sr_dbu)}] [expr {round(68*$::sr_dbu)}] [expr {round(1154*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s1: expected 26 DFFs, got $nc"}
sr_place $gr 60 1150
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(112*$::sr_dbu)}] [expr {round(1146*$::sr_dbu)}] [expr {round(128*$::sr_dbu)}] [expr {round(1154*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s2: expected 26 DFFs, got $nc"}
sr_place $gr 120 1150
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(182*$::sr_dbu)}] [expr {round(921*$::sr_dbu)}] [expr {round(198*$::sr_dbu)}] [expr {round(929*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s3: expected 26 DFFs, got $nc"}
sr_place $gr 190 925
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l0_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(232*$::sr_dbu)}] [expr {round(898*$::sr_dbu)}] [expr {round(248*$::sr_dbu)}] [expr {round(906*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l0_s4]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s4: expected 26 DFFs, got $nc"}
sr_place $gr 240 902
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$::sr_dbu)}] [expr {round(1176.32*$::sr_dbu)}] [expr {round(308*$::sr_dbu)}] [expr {round(1184.32*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s0[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s0: expected 26 DFFs, got $nc"}
sr_place $gr 300 1180.32
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(1006*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(1014*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s1[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s1: expected 26 DFFs, got $nc"}
sr_place $gr 380.16 1010
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(192*$::sr_dbu)}] [expr {round(686*$::sr_dbu)}] [expr {round(208*$::sr_dbu)}] [expr {round(694*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s2[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s2: expected 26 DFFs, got $nc"}
sr_place $gr 200 690
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(436*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(444*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s3[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s3: expected 26 DFFs, got $nc"}
sr_place $gr 380.16 440
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk strap_l1_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(232*$::sr_dbu)}] [expr {round(284*$::sr_dbu)}] [expr {round(248*$::sr_dbu)}] [expr {round(292*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk strap_l1_s4]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s4[} $nm] >= 0 } { sr_bind $net $gr; incr nc; incr sn }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s4: expected 26 DFFs, got $nc"}
sr_place $gr 240 288
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
if {$sn != 260} {error "STRAP_REGION expected 260 DFFs"}
puts "STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed"
set rn 0
set rg [odb::dbRegion_create $::sr_blk rst_p0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(224*$::sr_dbu)}] [expr {round(1174.32*$::sr_dbu)}] [expr {round(240*$::sr_dbu)}] [expr {round(1182.32*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_p0]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.p0$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_p0: expected 1 register, got $nc"}
sr_place $gr 232 1178.32
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(1096*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(1104*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n1$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n1: expected 1 register, got $nc"}
sr_place $gr 380.16 1100
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(1036*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(1044*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n2: expected 1 register, got $nc"}
sr_place $gr 380.16 1040
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_n3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(976*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(984*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_n3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.n3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_n3: expected 1 register, got $nc"}
sr_place $gr 380.16 980
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gn]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(956*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(964*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gn]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gn$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gn: expected 1 register, got $nc"}
sr_place $gr 380.16 960
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_lhn]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(936*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(944*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_lhn]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_lhn$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_lhn: expected 1 register, got $nc"}
sr_place $gr 380.16 940
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_t1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(856*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(864*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_t1]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.t1$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_t1: expected 1 register, got $nc"}
sr_place $gr 380.16 860
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_m2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(756*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(764*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_m2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.m2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_m2: expected 1 register, got $nc"}
sr_place $gr 380.16 760
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_m3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(212*$::sr_dbu)}] [expr {round(696*$::sr_dbu)}] [expr {round(228*$::sr_dbu)}] [expr {round(704*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_m3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.m3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_m3: expected 1 register, got $nc"}
sr_place $gr 220 700
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gm]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(212*$::sr_dbu)}] [expr {round(676*$::sr_dbu)}] [expr {round(228*$::sr_dbu)}] [expr {round(684*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gm]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gm$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gm: expected 1 register, got $nc"}
sr_place $gr 220 680
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_ptw]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(92*$::sr_dbu)}] [expr {round(636*$::sr_dbu)}] [expr {round(108*$::sr_dbu)}] [expr {round(644*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_ptw]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_ptw$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_ptw: expected 1 register, got $nc"}
sr_place $gr 100 640
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_pte]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(207*$::sr_dbu)}] [expr {round(636*$::sr_dbu)}] [expr {round(223*$::sr_dbu)}] [expr {round(644*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_pte]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_pte$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_pte: expected 1 register, got $nc"}
sr_place $gr 215 640
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_t2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(212*$::sr_dbu)}] [expr {round(556*$::sr_dbu)}] [expr {round(228*$::sr_dbu)}] [expr {round(564*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_t2]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.t2$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_t2: expected 1 register, got $nc"}
sr_place $gr 220 560
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(396*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(404*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_s3]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.s3$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_s3: expected 1 register, got $nc"}
sr_place $gr 380.16 400
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_gs]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(356*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(364*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_gs]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_gs$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_gs: expected 1 register, got $nc"}
sr_place $gr 380.16 360
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
set rg [odb::dbRegion_create $::sr_blk rst_f_lhs]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(372.16*$::sr_dbu)}] [expr {round(336*$::sr_dbu)}] [expr {round(388.16*$::sr_dbu)}] [expr {round(344*$::sr_dbu)}]
set gr [odb::dbGroup_create $::sr_blk rst_f_lhs]
set nc 0
foreach net [$::sr_blk getNets] {
  set nm [string map {\\ {}} [$net getName]]
  if {[regexp {u_rt\.f_lhs$} $nm]} { sr_bind $net $gr; incr nc; incr rn }
}
if {$nc != 1} {error "RESET_STATION rst_f_lhs: expected 1 register, got $nc"}
sr_place $gr 380.16 340
odb::dbGroup_destroy $gr
odb::dbRegion_destroy $rg
if {$rn != 16} {error "RESET_STATION expected 16 registers"}
puts "RESET_STATION_PLACED 16 FIXED_CELLS $::sr_fixed"
# el1013-smh-r14: g-lane relay / G1 select stations (window fill, nearest rows first, 1 um between cells)
proc sr_place_win {insts x0 y0 x1 y1} {
  set X0 [expr {round($x0*$::sr_dbu)}]; set Y0 [expr {round($y0*$::sr_dbu)}]; set X1 [expr {round($x1*$::sr_dbu)}]; set Y1 [expr {round($y1*$::sr_dbu)}]
  set cy [expr {($Y0+$Y1)/2}]; set rows {}; set pad [expr {round(1.0*$::sr_dbu)}]
  foreach r $::sr_rows {lassign $r ox oy xe ori; if {$oy >= $Y0 && $oy+$::sr_rh <= $Y1 && $xe > $X0 && $ox < $X1} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}
  set rows [lsort -integer -index 0 $rows]
  foreach i $insts {
    set h [[$i getMaster] getHeight]; set w [expr {max([[$i getMaster] getWidth],$::sr_mw_dff)+4*$::sr_sw+$pad}]; set found 0
    foreach r $rows {lassign $r delta ox oy xe ori
      set x [expr {$ox+int(ceil(double(max($ox,$X0)-$ox)/$::sr_sw))*$::sr_sw}]
      while {$x+$w <= min($xe,$X1)} {
        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {
          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}
        }
        if {$jump > $x} {set x $jump; continue}
        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break
      }; if {$found} break
    }; if {!$found} {error "G_STATION no legal site for [$i getName] in ($x0 $y0 $x1 $y1)"}
  }
}
# el1013-smh-r16: operand relay registers IN PIN ORDER.  r15 GRT (EARLY_FAIL_CONGESTION, both tiles): sr_place_win filled
# the xb window in instance order, so a register sat anywhere in the 100-um window: its Q net ran sideways to its
# bdc pin and its D net sideways from the x store (GRT: the 30.26-um leaf-1 gap full, H capacity 22 / usage 23 a
# gcell at the window centre; markers on xb_w / xb_x / iw / ix nets only; the 58.32-um leaf-0 gap clean).
# sr_pin_x: x of the hard-child pin a register drives (through <= 3 BUF / INV).
proc sr_pin_x {i} {
  set cur $i
  for {set hop 0} {$hop < 4} {incr hop} {
    set nxt {}
    foreach it [$cur getITerms] { if {![$it isOutputSignal]} continue; set n [$it getNet]; if {$n eq "NULL"} continue
      foreach jt [$n getITerms] { if {![$jt isInputSignal]} continue; set j [$jt getInst]
        if {[[$j getMaster] isBlock]} { set bb [$jt getBBox]; return [expr {([$bb xMin]+[$bb xMax])/2}] }
        if {[regexp {^(BUF|INV)} [[$j getMaster] getName]]} { set nxt $j } } }
    if {$nxt eq {}} break; set cur $nxt
  }; return -1
}
proc sr_sort_pin_x {insts} {
  set l {}; foreach i $insts {lappend l [list [sr_pin_x $i] [$i getName] $i]}
  set o {}; foreach e [lsort -integer -index 0 [lsort -dictionary -index 1 $l]] {lappend o [lindex $e 2]}; return $o
}
# sr_place_cols: every register in the row nearest the window centre that is free AT THE X OF ITS PIN (the Q net is a
# vertical drop on the pin's own track column); a register with no pin or no free row takes the ordered window fill.
proc sr_place_cols {insts x0 y0 x1 y1} {
  set X0 [expr {round($x0*$::sr_dbu)}]; set Y0 [expr {round($y0*$::sr_dbu)}]; set X1 [expr {round($x1*$::sr_dbu)}]; set Y1 [expr {round($y1*$::sr_dbu)}]
  set cy [expr {($Y0+$Y1)/2}]; set rows {}; set pad [expr {round(1.0*$::sr_dbu)}]; set rest {}; set ncol 0
  foreach r $::sr_rows {lassign $r ox oy xe ori; if {$oy >= $Y0 && $oy+$::sr_rh <= $Y1 && $xe > $X0 && $ox < $X1} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}
  set rows [lsort -integer -index 0 $rows]
  foreach i [sr_sort_pin_x $insts] {
    set px [sr_pin_x $i]; if {$px < 0} {lappend rest $i; continue}
    set h [[$i getMaster] getHeight]; set w [expr {max([[$i getMaster] getWidth],$::sr_mw_dff)+4*$::sr_sw+$pad}]; set found 0
    foreach r $rows {lassign $r delta ox oy xe ori
      set x [expr {max($X0,min($px-$w/2,min($xe,$X1)-$w))}]; set x [expr {$ox+int(floor(double($x-$ox)/$::sr_sw))*$::sr_sw}]
      if {$x < $ox || $x+$w > $xe} continue
      set free 1; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {
        if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set free 0; break}}
        if {!$free} break }
      if {!$free} continue
      $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; incr ncol; break
    }; if {!$found} {lappend rest $i}
  }
  if {[llength $rest]} {sr_place_win $rest $x0 $y0 $x1 $y1}
  puts "X_STATION_COLS $ncol registers at their pin column, [llength $rest] by ordered window fill"
}
set gn 0
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_gl\[[0-9]\]\.u_[dv]2/q\[[0-9]+\]\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 100} {error "G_STATION g_pass2: expected 100 registers, got [llength $gl]"}
sr_place_win $gl 183.0 594.0 217.0 606.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[0\]\.u_lh\.g[ytvf](_q)?(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION g1_l0: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 63.0 1115.0 83.0 1129.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[0\]\.u_gr[dv]1/q\[[0-9]+\]\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION grd1_l0: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 374.16 894.0 386.16 906.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[0\]\.u_gr[dv]2/q\[[0-9]+\]\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION grd2_l0: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 184.0 514.0 216.0 526.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[1\]\.u_lh\.g[ytvf](_q)?(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION g1_l1: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 63.0 63.0 83.0 77.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[1\]\.u_gr[dv]1/q\[[0-9]+\]\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION grd1_l1: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 374.16 114.0 386.16 126.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[1\]\.u_gr[dv]2/q\[[0-9]+\]\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] != 50} {error "G_STATION grd2_l1: expected 50 registers, got [llength $gl]"}
sr_place_win $gl 374.16 34.0 386.16 46.0
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[0\]\.u_lh\.xb_[a-z0-9]+(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] < 1000 || [llength $gl] > 1084} {error "G_STATION xb_l0: expected 1000..1084 registers, got [llength $gl]"}
sr_place_cols $gl 23.4 909.24 123.4 933.24
puts "X_STATION xb_l0 [llength $gl]"
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[0\]\.u_lh\.xf_[a-z0-9]+(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] < 480 || [llength $gl] > 531} {error "G_STATION xf_l0: expected 480..531 registers, got [llength $gl]"}
sr_place_win [sr_sort_pin_x $gl] 250.0 914.24 330.0 928.24
puts "X_STATION xf_l0 [llength $gl]"
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[1\]\.u_lh\.xb_[a-z0-9]+(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] < 1000 || [llength $gl] > 1084} {error "G_STATION xb_l1: expected 1000..1084 registers, got [llength $gl]"}
sr_place_cols $gl 23.4 271.88 123.4 291.88
puts "X_STATION xb_l1 [llength $gl]"
incr gn [llength $gl]
set gl {}
foreach i [$::sr_blk getInsts] {set nm [string map {\\ {}} [$i getName]]; if {[regexp {g_lf\[1\]\.u_lh\.xf_[a-z0-9]+(\[[0-9]+\])?\$_DFF} $nm] && [string match DFF* [[$i getMaster] getName]]} {lappend gl $i}}
if {[llength $gl] < 480 || [llength $gl] > 531} {error "G_STATION xf_l1: expected 480..531 registers, got [llength $gl]"}
sr_place_win [sr_sort_pin_x $gl] 250.0 269.88 330.0 283.88
puts "X_STATION xf_l1 [llength $gl]"
incr gn [llength $gl]
puts "G_STATION_PLACED 11 DFFS $gn FIXED_CELLS $::sr_fixed"
