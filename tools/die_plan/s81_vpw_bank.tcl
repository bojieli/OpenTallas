# Opt-in S81 form-B VPW bank-end placement. Source AFTER face_flops.tcl,
# before GPL. No netlist edits. Matched FFs go FIRM on the free legal sites
# nearest to either real SRAM box (blocked/occupied sites excluded).
# FIX-S81-VPW 11-17 (FABLE-CLOSURE-STRATEGY lever 6.1):
#  - a block with no VP SRAM macros and no VPW FFs (col, non-VP types) is
#    skipped with a no-op clock record instead of failing;
#  - sites are ordered by distance to the NEAREST bank box, not to the
#    centroid of both banks (t10/t74 banks ~420 um apart: every centroid site
#    was > 100 um from both banks, so the first FF failed);
#  - under R-MINIMAL an FF with no site within 100 um is a WARN and is left
#    to GPL (not FIRM), never a place stop.
# XR-MID-1 (S81-GEOM-OPUS 11-18, FABLE-PD-S81-0855 fix 2): OT_S81_VPW_XR_MID=MIN:D (plan budgets.vpw_xr_mid_types).
# When the VS core to nearest VP bank distance W is over MIN um, the XR cohort (write-port flops under g_xr) is taken
# out of the bank set and placed FIRM on free sites nearest the point at min(D, W/2) um from the VS core along the
# VS-to-bank line, so the first cycle carries d um of wire and the second W-d; the tap group excludes g_xr (those
# flops take their nearest tap).  0 cycles, no RTL change.  Unset = the bank form unchanged.
proc vb_noop_clock {why} {
  set f [open /work/vpw_bank_clock.tcl w]
  puts $f "# OT_VPW_BANK skipped: $why (no tap group)"
  close $f
  puts "OT_VPW_BANK SKIP $why"
}
uplevel #0 {
set vb_skip ""
set vb_b [ord::get_db_block]
set vb_u [[ord::get_db_tech] getDbUnitsPerMicron]
set vb_core [$vb_b getCoreArea]
set vb_banks {}; set vb_ffs {}; set vb_blocks {};set vb_groups {}
foreach i [$vb_b getInsts] {
  set m [$i getMaster]; set n [$i getName]
  if {[$m isBlock]} {
    set bb [$i getBBox]
    lappend vb_blocks [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    if {[regexp {(^|[._/])vp[._/]u_b[01]$} $n]} {lappend vb_banks $i}
  }
  if {[regexp {(^|[._/])vp[._/]g_wr1[._/]u_w[._/]} $n] && [string match *DFF* [$m getName]]} {
    lappend vb_ffs $i
    regexp {^(.*[._/]vp[._/]g_wr1[._/]u_w)[._/]} $n -> group
    dict set vb_groups $group 1
  }
}
if {![llength $vb_banks] && ![llength $vb_ffs]} {set vb_skip "no VP SRAM macros and no VPW FFs in this block"}
if {$vb_skip eq ""} {
if {[llength $vb_banks] != 2} {error "OT_VPW_BANK needs exactly two real VP SRAM macros, got [llength $vb_banks]"}
if {![llength $vb_ffs]} {error "OT_VPW_BANK found no VPW FFs; hierarchy/RTL mismatch"}
if {[dict size $vb_groups]!=1} {error "OT_VPW_BANK needs one leaf write-port group"}
set vb_group [lindex [dict keys $vb_groups] 0]
set vb_x0 1e30;set vb_y0 1e30;set vb_x1 -1e30;set vb_y1 -1e30
foreach i $vb_banks {
  set q [$i getBBox]
  set vb_x0 [expr {min($vb_x0,[$q xMin])}];set vb_x1 [expr {max($vb_x1,[$q xMax])}]
  set vb_y0 [expr {min($vb_y0,[$q yMin])}];set vb_y1 [expr {max($vb_y1,[$q yMax])}]
}
set vb_cx [expr {($vb_x0+$vb_x1)/2.0}];set vb_cy [expr {($vb_y0+$vb_y1)/2.0}]
set vb_margin [expr {40*$vb_u}]
set vb_rx0 [expr {max([$vb_core xMin],$vb_x0-$vb_margin)}]
set vb_rx1 [expr {min([$vb_core xMax],$vb_x1+$vb_margin)}]
set vb_ry0 [expr {max([$vb_core yMin],$vb_y0-$vb_margin)}]
set vb_ry1 [expr {min([$vb_core yMax],$vb_y1+$vb_margin)}]
set vb_own {};foreach i $vb_ffs {dict set vb_own $i 1}
set vb_allffs $vb_ffs
# Real placement obstructions and fixed cells, including die-clock reserves.
foreach q [$vb_b getBlockages] {set r [$q getBBox];lappend vb_blocks [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}
foreach i [$vb_b getInsts] {
  if {[dict exists $vb_own $i] || [$i getPlacementStatus] ni {FIRM LOCKED}} continue
  if {[[$i getMaster] isBlock]} continue
  set q [$i getBBox];lappend vb_blocks [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]
}
set vb_xr_n 0
if {[info exists ::env(OT_S81_VPW_XR_MID)] && $::env(OT_S81_VPW_XR_MID) ne ""} {
  lassign [split $::env(OT_S81_VPW_XR_MID) :] vb_xmin vb_xd
  set vb_vs {}
  foreach i [$vb_b getInsts] {if {[[$i getMaster] isBlock] && [regexp {(^|[._/])u_vs$} [$i getName]]} {lappend vb_vs $i}}
  set vb_xr {};set vb_rest {}
  foreach i $vb_ffs {if {[regexp {[._/]g_xr[._/]} [$i getName]]} {lappend vb_xr $i} else {lappend vb_rest $i}}
  if {[llength $vb_vs]!=1 || ![llength $vb_xr]} {
    puts "OT_VPW_XR_MID SKIP vs_cores=[llength $vb_vs] xr_ffs=[llength $vb_xr]"
  } else {
    set q [[lindex $vb_vs 0] getBBox]
    set vb_W 1e30
    foreach bi $vb_banks {
      set r [$bi getBBox]
      set pa {};set pb {}
      foreach {lo0 hi0 lo1 hi1} [list [$q xMin] [$q xMax] [$r xMin] [$r xMax] [$q yMin] [$q yMax] [$r yMin] [$r yMax]] {
        if {$hi0 < $lo1} {lappend pa $hi0;lappend pb $lo1} elseif {$hi1 < $lo0} {lappend pa $lo0;lappend pb $hi1} else {
          set m [expr {(max($lo0,$lo1)+min($hi0,$hi1))/2}];lappend pa $m;lappend pb $m}
      }
      set w [expr {abs([lindex $pa 0]-[lindex $pb 0])+abs([lindex $pa 1]-[lindex $pb 1])}]
      if {$w < $vb_W} {set vb_W $w;set vb_pa $pa;set vb_pb $pb}
    }
    if {$vb_W <= $vb_xmin*$vb_u} {
      puts "OT_VPW_XR_MID KEEP bank form: VS-to-bank [expr {$vb_W/double($vb_u)}]um <= $vb_xmin um"
    } else {
      set vb_d [expr {min($vb_xd*$vb_u, $vb_W/2.0)}]
      set f [expr {$vb_d/double($vb_W)}]
      set vb_tx [expr {[lindex $vb_pa 0]+([lindex $vb_pb 0]-[lindex $vb_pa 0])*$f}]
      set vb_ty [expr {[lindex $vb_pa 1]+([lindex $vb_pb 1]-[lindex $vb_pa 1])*$f}]
      set vb_win [expr {120*$vb_u}]
      set vb_mid {};set mw 0;set mh 0
      foreach i $vb_xr {set m [$i getMaster];set mw [expr {max($mw,[$m getWidth])}];set mh [expr {max($mh,[$m getHeight])}]}
      foreach r [$vb_b getRows] {
        lassign [$r getOrigin] x y
        set st [$r getSite];set sw [$st getWidth];set rh [$st getHeight]
        if {$rh!=$mh || abs($y-$vb_ty)>$vb_win} continue
        set rr [$r getBBox]
        set x0 [expr {max([$rr xMin],$vb_tx-$vb_win)}];set x1 [expr {min([$rr xMax],$vb_tx+$vb_win)}]
        set pitch [expr {int(ceil(2.0*$mw/$sw))*$sw}]
        set x0 [expr {$x+int(ceil(double($x0-$x)/$sw))*$sw}]
        for {set px $x0} {$px+$mw<=$x1} {incr px $pitch} {
          set blocked 0
          foreach bq $vb_blocks {
            lassign $bq a b c d
            if {$px<$c && $a<$px+$mw && $y<$d && $b<$y+$mh} {set blocked 1;break}
          }
          if {$blocked} continue
          lappend vb_mid [list [expr {abs($px-$vb_tx)+abs($y-$vb_ty)}] $px $y [$r getOrient]]
        }
      }
      set vb_mid [lsort -real -index 0 $vb_mid]
      set vb_xo [open /work/vpw_xr_mid_sites.tsv w];puts $vb_xo "inst\tx_um\ty_um\ttarget_distance_um"
      set k 0;set vb_xworst 0;set vb_xgpl 0
      foreach i [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $vb_xr] {
        if {$k>=[llength $vb_mid]} {incr vb_xgpl;continue}
        lassign [lindex $vb_mid $k] dd x y orient
        $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
        lappend vb_blocks [list $x $y [expr {$x+$mw}] [expr {$y+$mh}]]
        puts $vb_xo "[$i getName]\t[expr {$x/double($vb_u)}]\t[expr {$y/double($vb_u)}]\t[expr {$dd/double($vb_u)}]"
        set vb_xworst [expr {max($vb_xworst,$dd)}];incr k
      }
      close $vb_xo
      set vb_xr_n $k
      set vb_ffs $vb_rest
      puts "OT_VPW_XR_MID placed $k of [llength $vb_xr] XR FFs FIRM at [expr {$vb_d/double($vb_u)}]um from VS (VS-to-bank [expr {$vb_W/double($vb_u)}]um), target ([expr {$vb_tx/double($vb_u)}],[expr {$vb_ty/double($vb_u)}]) worst [expr {$vb_xworst/double($vb_u)}]um; left to GPL $vb_xgpl"
    }
  }
}
set vb_keep {}
foreach q $vb_blocks {
  lassign $q a b c d
  if {$a<$vb_rx1 && $c>$vb_rx0 && $b<$vb_ry1 && $d>$vb_ry0} {lappend vb_keep $q}
}
set vb_blocks $vb_keep
set vb_rows {};set vb_maxw 0;set vb_maxh 0
foreach i $vb_ffs {set m [$i getMaster];set vb_maxw [expr {max($vb_maxw,[$m getWidth])}];set vb_maxh [expr {max($vb_maxh,[$m getHeight])}]}
foreach r [$vb_b getRows] {
  lassign [$r getOrigin] x y
  set st [$r getSite];set sw [$st getWidth];set rh [$st getHeight]
  if {$y<$vb_ry0 || $y+$vb_maxh>$vb_ry1 || $rh!=$vb_maxh} continue
  set rr [$r getBBox]
  set x0 [expr {max([$rr xMin],$vb_rx0)}];set x1 [expr {min([$rr xMax],$vb_rx1)}]
  set pitch [expr {int(ceil(2.0*$vb_maxw/$sw))*$sw}]
  set x0 [expr {$x+int(ceil(double($x0-$x)/$sw))*$sw}]
  for {set px $x0} {$px+$vb_maxw<=$x1} {incr px $pitch} {
    set blocked 0
    foreach q $vb_blocks {
      lassign $q a b c d
      if {$px<$c && $a<$px+$vb_maxw && $y<$d && $b<$y+$vb_maxh} {set blocked 1;break}
    }
    if {$blocked} continue
    set dist 1e30
    foreach bi $vb_banks {
      set q [$bi getBBox]
      set dist [expr {min($dist,max(0,[$q xMin]-$px,$px-[$q xMax])+max(0,[$q yMin]-$y,$y-[$q yMax]))}]
    }
    lappend vb_rows [list $dist $px $y [$r getOrient]]
  }
}
set vb_rows [lsort -real -index 0 $vb_rows]
set vb_out [open /work/vpw_bank_sites.tsv w];puts $vb_out "inst\tx_um\ty_um\tbank_distance_um"
set vb_n 0;set vb_worst 0;set vb_gpl 0
foreach i [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $vb_ffs] {
  if {$vb_n>=[llength $vb_rows]} {incr vb_gpl;continue}
  lassign [lindex $vb_rows $vb_n] dist x y orient
  set bd 1e30
  foreach bi $vb_banks {
    set q [$bi getBBox]
    set d [expr {max(0,[$q xMin]-$x,$x-[$q xMax])+max(0,[$q yMin]-$y,$y-[$q yMax])}]
    set bd [expr {min($bd,$d)}]
  }
  if {$bd>100*$vb_u} {incr vb_gpl;continue}
  $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
  puts $vb_out "[$i getName]\t[expr {$x/double($vb_u)}]\t[expr {$y/double($vb_u)}]\t[expr {$bd/double($vb_u)}]"
  set vb_worst [expr {max($vb_worst,$bd)}];incr vb_n
}
close $vb_out
if {$vb_gpl} {puts "OT_VPW_BANK WARN $vb_gpl of [llength $vb_ffs] FFs have no free site within 100um of a bank; left to GPL"}
# Persist a standard-tap group for the later CTS process. Core taps clk_c*
# have early hard-macro contracts and are never candidates.
set vb_tap {};set vb_td 1e30
foreach bt [$vb_b getBTerms] {
  if {![regexp {^clk(_t[0-9]+)?$} [$bt getName]]} continue
  set bb [$bt getBBox]
  set dd [expr {abs(([$bb xMin]+[$bb xMax])/2.0-$vb_cx)+abs(([$bb yMin]+[$bb yMax])/2.0-$vb_cy)}]
  if {$dd<$vb_td} {set vb_td $dd;set vb_tap [$bt getName]}
}
if {$vb_tap eq ""} {error "OT_VPW_BANK no standard clock tap"}
set vb_clk [open /work/vpw_bank_clock.tcl w]
puts $vb_clk {if {[info exists ::env(OT_TAP_GROUP_RE)] && $::env(OT_TAP_GROUP_RE) ne "" && $::env(OT_TAP_GROUP_RE) ne {^(.*[._/]vp[._/]g_wr1[._/]u_w)[._/]}} {error "OT_VPW_BANK conflicts with an existing clock group; combine groups explicitly"}}
if {$vb_xr_n} {puts $vb_clk {set ::env(OT_TAP_GROUP_RE) {^(.*[._/]vp[._/]g_wr1[._/]u_w)[._/](?!g_xr[._/])}}} else {puts $vb_clk {set ::env(OT_TAP_GROUP_RE) {^(.*[._/]vp[._/]g_wr1[._/]u_w)[._/]}}}
puts $vb_clk "set ::env(OT_TAP_GROUP_FIXED) {$vb_group:$vb_tap}"
close $vb_clk
puts "OT_VPW_BANK_CLOCK $vb_tap at [expr {$vb_td/double($vb_u)}]um from bank centroid"
puts "OT_VPW_BANK placed $vb_n FFs FIRM, nearest-bank max [expr {$vb_worst/double($vb_u)}]um; legal sites [llength $vb_rows]; bounds [list [expr {$vb_rx0/$vb_u}] [expr {$vb_ry0/$vb_u}] [expr {$vb_rx1/$vb_u}] [expr {$vb_ry1/$vb_u}]]"
} else {vb_noop_clock $vb_skip}
}
