# Modelled structural correction: the four actual SRAM prefetch/capture groups
# live beside their own west-face 128-bit read-pin quarter, rather than in
# opposite channels with a return detour. Keep every register and every edge.
set ot_b128_b [ord::get_db_block]
set ot_b128_u [$ot_b128_b getDbUnitsPerMicron]
set ot_b128_macros {}
foreach i [$ot_b128_b getInsts] {
 if {[[$i getMaster] isBlock]} {lappend ot_b128_macros $i}
}
if {[llength $ot_b128_macros] != 1} {error "BANK128 requires exactly one actual SRAM macro"}
set ot_b128_m [lindex $ot_b128_macros 0]
if {[$ot_b128_m getOrient] ne "R0"} {error "BANK128 read-pin quarter homes require the granted R0 SRAM"}
set ot_b128_box [$ot_b128_m getBBox]
set ot_b128_mx [expr {[$ot_b128_box xMin]/double($ot_b128_u)}]
set ot_b128_my [expr {[$ot_b128_box yMin]/double($ot_b128_u)}]
set ot_b128_core [$ot_b128_b getCoreArea]
set ot_b128_x0 [$ot_b128_core xMin]
set ot_b128_x1 [expr {int(round(($ot_b128_mx-1.08)*$ot_b128_u))}]
if {$ot_b128_x1-$ot_b128_x0 < 18*$ot_b128_u} {error "BANK128 west channel is narrower than the actual model"}
for {set g 0} {$g<4} {incr g} {
 set yy0 [expr {floor(($ot_b128_my+1.536+12.288*$g)/0.27)*0.27}]
 set yy1 [expr {floor(($ot_b128_my+1.536+12.288*($g+1))/0.27)*0.27}]
 set y0 [expr {int(round($yy0*$ot_b128_u))}]
 set y1 [expr {int(round($yy1*$ot_b128_u))}]
 set cells {};set area 0
 foreach i [$ot_b128_b getInsts] {
  set n [string map {\\ ""} [$i getName]]
  if {[string first "u_fifo.g_esl.g_s\[$g\]." $n] == 0} {
   set m [$i getMaster]
   if {![$m isBlock]} {lappend cells $i;set area [expr {$area+[$m getWidth]*[$m getHeight]}]}
  }
 }
 if {[llength $cells]<259} {error "BANK128 actual group $g has only [llength $cells] cells, expected >=259 real FF/control owners"}
 set capacity [expr {($ot_b128_x1-$ot_b128_x0)*($y1-$y0)}]
 set density [expr {$area/double($capacity)}]
 if {$density>0.60} {error "BANK128 actual group $g density $density exceeds0.60; request wider legal channel, do not silently fit"}
 set r [odb::dbRegion_create $ot_b128_b "bank128_group_$g"]
 odb::dbBox_create $r $ot_b128_x0 $y0 $ot_b128_x1 $y1
 $r setRegionType INCLUSIVE
 set grp [odb::dbGroup_create $r "bank128_group_$g"]
 foreach i $cells {$grp addInst $i}
 puts "BANK128_REAL_GROUP $g cells [llength $cells] density $density box $ot_b128_x0 $y0 $ot_b128_x1 $y1"
}
