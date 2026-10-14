# Place each bit's small OR cone between its real fixed input and output flops.
# No net, cell or timing constraint changes. Real routing still decides signoff.
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
global gocc gxstep gystep gbasey gminx gmaxx gnrow
set gb [ord::get_db_block]
set gd [[ord::get_db_tech] getDbUnitsPerMicron]
set gc [$gb getCoreArea]
set rows [$gb getRows]
if {[llength $rows]==0} {error "GATHER_BIT: no physical rows"}
set site [[lindex $rows 0] getSite]
set gxstep [$site getWidth];set gystep [$site getHeight]
set gbasey [$gc yMin];set gminx [$gc xMin];set gmaxx [$gc xMax];set gmaxy [$gc yMax]
set gnrow [expr {int(($gmaxy-$gbasey)/$gystep)}]
array set gocc {}
array set ::gorient {}
foreach gr $rows {
 lassign [$gr getOrigin] rx ry
 set ri [expr {int(round(($ry-$gbasey)/double($gystep)))}]
 set ::gorient($ri) [$gr getOrient]
}
proc g_reserve {rect} {
 upvar #0 gocc occ gbasey by gystep sy
 set lo [expr {int(floor(([$rect yMin]-$by)/double($sy)))}]
 set hi [expr {int(floor(([$rect yMax]-1-$by)/double($sy)))}]
 for {set r $lo} {$r<=$hi} {incr r} {lappend occ($r) [list [$rect xMin] [$rect xMax]]}
}
foreach inst [$gb getInsts] {
 if {[$inst getPlacementStatus] in {FIRM LOCKED}} {g_reserve [$inst getBBox]}
}
proc g_upstream_ff {net depth} {
 if {$depth>12 || $net eq "NULL"} {return ""}
 set d [ot_of_drv $net];if {$d eq ""} {return ""}
 set i [$d getInst];if {[ot_of_isff $i]} {return $i}
 foreach it [$i getITerms] {
  if {[$it isInputSignal]} {set f [g_upstream_ff [$it getNet] [expr {$depth+1}]];if {$f ne ""} {return $f}}
 }
 return ""
}
proc g_cone {net depth coneName leafName} {
 upvar $coneName cone $leafName leaf
 if {$depth>12} {error "GATHER_BIT: unexpectedly deep combinational cone"}
 if {$net eq "NULL"} {return}
 set d [ot_of_drv $net];if {$d eq ""} {return}
 set i [$d getInst];set n [$i getName]
 if {[ot_of_isff $i]} {dict set leaf $n $i;return}
 if {[dict exists $cone $n]} {return}
 dict set cone $n $i
 foreach it [$i getITerms] {if {[$it isInputSignal]} {g_cone [$it getNet] [expr {$depth+1}] cone leaf}}
}
proc g_place {inst tx ty} {
 upvar #0 gocc occ gxstep sx gystep sy gbasey by gminx xmin gmaxx xmax gnrow nr
 set w [[$inst getMaster] getWidth];set h [[$inst getMaster] getHeight]
 set rh [expr {int(ceil($h/double($sy)))}]
 set r0 [expr {max(0,min($nr-$rh,int(round(($ty-$by)/double($sy)))))}]
 for {set rad 0} {$rad<$nr} {incr rad} {
  foreach r [list [expr {$r0+$rad}] [expr {$r0-$rad}]] {
   if {$r<0 || $r+$rh>$nr} {continue}
   set x [expr {$xmin+int(round(($tx-$xmin)/double($sx)))*$sx}]
   if {$x<$xmin || $x+$w>$xmax} {set x $xmin}
   for {set tries 0} {$tries<1000 && $x+$w<=$xmax} {incr tries} {
    set end $x
    for {set rr $r} {$rr<$r+$rh} {incr rr} {
     if {![info exists occ($rr)]} {continue}
     foreach iv $occ($rr) {
      lassign $iv a b
      if {$x<$b && $x+$w>$a} {set end [expr {max($end,$b)}]}
     }
    }
    if {$end==$x} {
     if {![info exists ::gorient($r)]} {error "GATHER_BIT: missing actual site row $r"}
     $inst setOrient $::gorient($r)
     $inst setLocation $x [expr {$by+$r*$sy}]
     $inst setPlacementStatus FIRM
     g_reserve [$inst getBBox]
     return
    }
    set x [expr {$xmin+int(ceil(($end-$xmin)/double($sx)))*$sx}]
   }
  }
 }
 error "GATHER_BIT: no legal site for [$inst getName]"
}
set placed {};set gn 0;set bits 0
for {set b 0} {$b<1024} {incr b} {
 set port [$gb findBTerm [format {x[%d]} $b]]
 if {$port eq "NULL"} {error "GATHER_BIT: missing x bit $b"}
 set ff [g_upstream_ff [$port getNet] 0]
 if {$ff eq ""} {error "GATHER_BIT: x bit $b has no launching register"}
 set dp [$ff findITerm D]
 if {$dp eq "NULL"} {error "GATHER_BIT: missing flop D for x bit $b"}
 set cone {};set leaf {};g_cone [$dp getNet] 0 cone leaf
 if {[dict size $leaf]!=4} {error "GATHER_BIT: bit $b has [dict size $leaf] leaves, expected4"}
 set out [$ff getBBox]
 set xmin [$out xMin];set xmax [$out xMax];set ymin [$out yMin];set ymax [$out yMax]
 dict for {name i} $leaf {
  set box [$i getBBox]
  set xmin [expr {min($xmin,[$box xMin])}];set xmax [expr {max($xmax,[$box xMax])}]
  set ymin [expr {min($ymin,[$box yMin])}];set ymax [expr {max($ymax,[$box yMax])}]
 }
 set tx [expr {($xmin+$xmax)/2}];set ty [expr {($ymin+$ymax)/2}]
 dict for {name i} $cone {
  if {[dict exists $placed $name]} {continue}
  g_place $i $tx $ty;dict set placed $name 1;incr gn
 }
 incr bits
}
puts "GATHER_BIT placed $gn combinational cells for $bits exact bit cones (register endpoints preserved)"
