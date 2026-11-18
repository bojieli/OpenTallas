# S81 SerDes compact reset authority form; default off. Pure placement: no net,
# RTL, clock identity, pipeline stage or timing constraint is changed.
# Run after txl_mid.tcl at POST_GLOBAL_PLACE, before repair_design and DPL.
namespace eval ot_serdes_reset_local {
 proc run {} {
  set b [ord::get_db_block]
  set dbu [expr {double([$b getDbUnitsPerMicron])}]
  set group {}; set anchors {}
  foreach i [$b getInsts] {
   set n [$i getName]
   if {[regexp {u_core\.(g_locksafe\.(u_hold\.|g_rst_rt\.)|rs_[rt]\\?\[)} $n]} {
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "OT_SERDES_RESET_LOCAL authority already fixed: $n"}
    dict set group $n $i
    if {[regexp {u_core\.rs_[rt]\\?\[} $n]} {
     lassign [$i getLocation] x y
     lappend anchors [list $x $y]
    }
   }
  }
  if {![dict size $group] || ![llength $anchors]} {error "OT_SERDES_RESET_LOCAL no reset authority/consumer anchors"}
  # Include the short logic and buffer cone between authority registers. Do not
  # move a shared data cone or clock distribution; stop at sequential/macros.
  set front [dict values $group]
  for {set d 0} {$d<4 && [llength $front]} {incr d} {
   set next {}
   foreach i $front {
    foreach t [$i getITerms] {
     set pin [[$t getMTerm] getName]
     if {$pin in {CLK CLKN CK CKN VDD VSS}} continue
     set net [$t getNet]
     if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} continue
     set its [$net getITerms]
     if {[llength $its]>16} continue
     foreach u $its {
      set j [$u getInst]; set m [$j getMaster]; set n [$j getName]
      if {[dict exists $group $n] || [$m isBlock] || [$m isSequential] || [$j getPlacementStatus] in {FIRM LOCKED COVER}} continue
      dict set group $n $j; lappend next $j
     }
    }
   }
   set front $next
  }
  # Anchor at native reset consumers, preserving the existing clock identities.
  # Compact physical locality lets CTS choose nearby leaves within EACH domain;
  # never splice clk and recovered-clock nets together.
  set xs {}; set ys {}
  foreach p $anchors {lappend xs [lindex $p 0];lappend ys [lindex $p 1]}
  set xs [lsort -integer $xs];set ys [lsort -integer $ys]
  set ax [lindex $xs [expr {[llength $xs]/2}]]
  set ay [lindex $ys [expr {[llength $ys]/2}]]
  set halo [expr {8.64*$dbu}];set macs {}
  foreach i [$b getInsts] {
   if {![[$i getMaster] isBlock]} continue
   set z [$i getBBox]
   lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]
  }
  set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set n [dict size $group];set side [expr {int(ceil(sqrt($n)))}]
  set pitch [expr {1.08*$dbu}]
  # Reserve a whole macro-free pocket, not independently projected points which
  # could straddle a macro wall.  Search around the consumers before moving any.
  set half [expr {($side+2)*$pitch/2.0}]
  set chosen {}
  for {set r 0} {$r<=200 && ![llength $chosen]} {incr r 5} {
   for {set ix -1} {$ix<=1 && ![llength $chosen]} {incr ix} {
    for {set iy -1} {$iy<=1} {incr iy} {
     set x [expr {$ax+$ix*$r*$dbu}];set y [expr {$ay+$iy*$r*$dbu}]
     set rect [list [expr {$x-$half}] [expr {$y-$half}] [expr {$x+$half}] [expr {$y+$half}]]
     lassign $rect x0 y0 x1 y1;lassign $core cx0 cy0 cx1 cy1
     if {$x0<$cx0 || $y0<$cy0 || $x1>$cx1 || $y1>$cy1} continue
     set hit 0
     foreach z $macs {lassign $z a c e f;if {$x0<$e && $x1>$a && $y0<$f && $y1>$c} {set hit 1;break}}
     if {!$hit} {set chosen $rect;break}
    }
   }
  }
  if {![llength $chosen]} {error "OT_SERDES_RESET_LOCAL no compact macro-free pocket within 200 um of consumers"}
  lassign $chosen x0 y0 x1 y1
  set k 0;set area 0.0
  foreach n [lsort [dict keys $group]] {
   set i [dict get $group $n]
   set m [$i getMaster];set area [expr {$area+[$m getWidth]*[$m getHeight]/($dbu*$dbu)}]
   set x [expr {int($x0+$pitch*(1+$k%$side))}]
   set y [expr {int($y0+$pitch*(1+$k/$side))}]
   $i setLocation $x $y;$i setPlacementStatus PLACED
   incr k
  }
  puts "OT_SERDES_RESET_LOCAL cells $k cell_area_um2 $area region_um [expr {$x0/$dbu}] [expr {$y0/$dbu}] [expr {$x1/$dbu}] [expr {$y1/$dbu}], unchanged clocks/nets; DPL remains responsible for legal sites"
 }
}
if {[info exists ::env(OT_SERDES_RESET_LOCAL)] && $::env(OT_SERDES_RESET_LOCAL) eq "1"} {ot_serdes_reset_local::run}
