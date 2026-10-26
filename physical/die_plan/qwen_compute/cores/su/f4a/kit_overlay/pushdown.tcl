# pushdown.tcl -- QC-SU-LAT-R3 (METHODOLOGY 12.2a1 PUSHDOWN, 12.8a): in-core islands WITHOUT holes, blockages or OBS.
# Sourced first in PRE_GLOBAL_PLACE.  (1) ck = M5 interior pin at the slice clock-entry point (die M9->M5 stack lands on it).
# (2) Die-owned feed-through drivers in the entry island, in the CORE netlist on dedicated ft ports, FIRM + dont_touch:
#       ft_ck_i -> ot_isl_ckft (BUFx16f) -> ft_ck_o      die clock tree/mesh node driver (clock-through arc)
#       ft_rst_i -> ot_isl_rstft (BUFx4f) -> ft_rst_o    regional reset repeater
#     No core logic on those ports.  (3) The core's own H-tree island drivers (root + entry chain in the entry island,
#     one BUFx24 per leaf island) are created FIRM at the plan coordinates of OT_MSCTS_SPEC (ot_h_fixed); the CTS build
#     (mscts_h.tcl) connects them.  Placement flows around FIRM cells; the M1/M2 follow-pins and PG run through.
source $::env(OT_MSCTS_SPEC)
set ::ot_b [ord::get_db_block]; set ::ot_u [[ord::get_db_tech] getDbUnitsPerMicron]
set ::ot_core [$::ot_b getCoreArea]
set ::ot_row0 [lindex [$::ot_b getRows] 0]; set ::ot_site [$::ot_row0 getSite]
set ::ot_sw [$::ot_site getWidth]; set ::ot_rh [$::ot_site getHeight]
set ::ot_taken {}
proc ot_pd_overlap {x0 y0 x1 y1} {
  foreach r $::ot_taken { lassign $r a0 b0 a1 b1; if {$x0 < $a1 && $x1 > $a0 && $y0 < $b1 && $y1 > $b0} { return 1 } }
  foreach i [$::ot_b getInsts] {
    set st [$i getPlacementStatus]; if {$st ni {FIRM LOCKED COVER} && ![string match "TAPCELL*" [[$i getMaster] getName]]} continue
    set bb [$i getBBox]; if {$x0 < [$bb xMax] && $x1 > [$bb xMin] && $y0 < [$bb yMax] && $y1 > [$bb yMin]} { return 1 }
  }
  return 0
}
proc ot_pd_row_orient {yd} {
  foreach r [$::ot_b getRows] { if {[lindex [$r getOrigin] 1] == $yd} { return [$r getOrient] } }
  return R0
}
proc ot_pd_fixed {name master x y} {
  set m [[ord::get_db] findMaster $master]; if {$m eq "NULL"} { error "pushdown: no master $master" }
  set i [$::ot_b findInst $name]; if {$i eq "NULL"} { set i [odb::dbInst_create $::ot_b $m $name] }
  set w [$m getWidth]; set h [$m getHeight]
  set cx [$::ot_core xMin]; set cy [$::ot_core yMin]
  set yd [expr {$cy + int(round((double($y * $::ot_u) - $h / 2.0 - $cy) / $::ot_rh)) * $::ot_rh}]
  set xd0 [expr {$cx + int(round((double($x * $::ot_u) - $w / 2.0 - $cx) / $::ot_sw)) * $::ot_sw}]
  foreach dy {0 1 -1 2 -2 3 -3} {
    set yy [expr {$yd + $dy * $::ot_rh}]
    for {set k 0} {$k < 80} {incr k} {
      foreach s {1 -1} {
        set xx [expr {$xd0 + $s * $k * $::ot_sw}]
        if {![ot_pd_overlap $xx $yy [expr {$xx + $w}] [expr {$yy + $h}]]} {
          $i setOrient [ot_pd_row_orient $yy]; $i setLocation $xx $yy; $i setPlacementStatus FIRM
          lappend ::ot_taken [list $xx $yy [expr {$xx + $w}] [expr {$yy + $h}]]
          return $i
        }
      }
    }
  }
  error "pushdown: no free site for $name near ($x, $y)"
}
proc ot_pd_port {name dir x y} {
  set bt [$::ot_b findBTerm $name]
  if {$bt eq "NULL"} {
    set n [$::ot_b findNet $name]; if {$n eq "NULL"} { set n [odb::dbNet_create $::ot_b $name] }
    set bt [odb::dbBTerm_create $n $name]; $bt setIoType $dir
  }
  place_pin -pin_name $name -layer M5 -location [list $x $y] -pin_size {0.024 0.384}
  return [$bt getNet]
}
lassign $ot_ms_root ot_rx ot_ry
# ck pin: slice clock entry (exact point; the island rect is the slice's 8.64 lattice rect)
set ot_px [expr {[info exists ::env(OT_CK_PIN_X)] ? $::env(OT_CK_PIN_X) : [expr {$ot_rx - 1.5}]}]
set ot_py [expr {[info exists ::env(OT_CK_PIN_Y)] ? $::env(OT_CK_PIN_Y) : $ot_ry}]
place_pin -pin_name ck -layer M5 -location [list $ot_px $ot_py] -pin_size {0.024 0.384}
# core H-tree fixed drivers (root, entry chain, leaf-island drivers)
foreach f $ot_h_fixed { lassign $f n m x y; ot_pd_fixed $n $m $x $y }
# die feed-through drivers in the entry island (pins on M5 inside the island, 1.296 um either side of the ck pin column)
set ot_fx0 [expr {$ot_px - 2.592}]; set ot_fx1 [expr {$ot_px + 2.592}]
set ni [ot_pd_port ft_ck_i INPUT $ot_fx0 [expr {$ot_py + 2.16}]]; set no [ot_pd_port ft_ck_o OUTPUT $ot_fx1 [expr {$ot_py + 2.16}]]
set ci [ot_pd_fixed ot_isl_ckft BUFx16f_ASAP7_75t_R $ot_px [expr {$ot_py + 2.16}]]
foreach it [$ci getITerms] { set mt [$it getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue; if {[$mt getIoType] eq "INPUT"} { $it connect $ni } else { $it connect $no } }
$ni setSigType CLOCK; $no setSigType CLOCK
set ri [ot_pd_port ft_rst_i INPUT $ot_fx0 [expr {$ot_py - 2.16}]]; set ro [ot_pd_port ft_rst_o OUTPUT $ot_fx1 [expr {$ot_py - 2.16}]]
set rr [ot_pd_fixed ot_isl_rstft BUFx4f_ASAP7_75t_R $ot_px [expr {$ot_py - 2.16}]]
foreach it [$rr getITerms] { set mt [$it getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue; if {[$mt getIoType] eq "INPUT"} { $it connect $ri } else { $it connect $ro } }
$ci setDoNotTouch 1; $rr setDoNotTouch 1; foreach n {ft_ck_i ft_ck_o ft_rst_i ft_rst_o} { [$::ot_b findNet $n] setDoNotTouch 1 }
puts [format "OT_PUSHDOWN ck M5 interior (%.3f, %.3f); %d core H-tree drivers FIRM at plan coords; die ft: ft_ck_i->ot_isl_ckft->ft_ck_o, ft_rst_i->ot_isl_rstft->ft_rst_o (FIRM, dont_touch); NO blockage / NO OBS" $ot_px $ot_py [llength $ot_h_fixed]]
foreach f $ot_h_fixed { set i [$::ot_b findInst [lindex $f 0]]; set l [$i getLocation]; puts [format "OT_PUSHDOWN fixed %s %s at (%.3f, %.3f)" [lindex $f 0] [lindex $f 1] [expr {[lindex $l 0]/double($::ot_u)}] [expr {[lindex $l 1]/double($::ot_u)}]] }
