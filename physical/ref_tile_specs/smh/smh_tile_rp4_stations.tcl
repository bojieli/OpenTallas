# RP4j gather-lane stations (rp4h gate: u.g_gl[2].u_d3 reg->reg -230.5; placer put the middle stage u_d2 at y 296..1232,
# so one hop was ~1,229 um under the leaf hard children). Middle stage of every N->S gather lane FIRM at mid-tile (free band
# x 150-380, y 530-1000): hops ~760 um each. No RTL/pin/cycle change. Procs as smh_tile_rp3_strap_regions.tcl.
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
      set x [expr {$ox+int(ceil(double(max($ox,$cx-30*$::sr_dbu)-$ox)/$::sr_sw))*$::sr_sw}]
      while {$x+$w <= min($xe,$cx+30*$::sr_dbu)} {
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
proc st_group {name pats cx cy expect} {
  set gr [odb::dbGroup_create $::sr_blk $name]; set n 0
  foreach i [$::sr_blk getInsts] {
    set nm [string map {\\ {}} [$i getName]]
    foreach p $pats { if {[string first $p $nm] == 0 && [string match *DFF* [[$i getMaster] getName]]} { $gr addInst $i; incr n; break } }
  }
  if {$n == 0} {error "RP4_STATION $name: no DFFs"} elseif {$n != $expect} {puts "RP4_STATION WARNING $name: expected $expect DFFs, got $n"}
  sr_place $gr $cx $cy
  odb::dbGroup_destroy $gr
  puts "RP4_STATION $name $n flops at ($cx, $cy)"
}
st_group gl2_mid {u.g_gl[2].u_v2/ u.g_gl[2].u_d2/} 205 765 50
st_group gl3_mid {u.g_gl[3].u_v2/ u.g_gl[3].u_d2/} 265 765 50
st_group lf0_mid {u.g_lf[0].u_grv2/ u.g_lf[0].u_grd2/} 325 700 50
puts "RP4_STATION fixed $::sr_fixed"
