# Leaf-owned physical clock delivery. No new source, clock port or SDC exception.
# Real BUF24 cells and real row/site geometry; all decisions are offline STA.
proc nb_cd_driver {net} {
 foreach it [$net getITerms] {if {[$it isOutputSignal]} {return $it}}
 return ""
}
proc nb_cd_dummy {inst} {
 if {![string match clkload* [$inst getName]]} {return 0}
 foreach it [$inst getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
  set n [$it getNet]
  if {$n eq "" || $n eq "NULL"} continue
  if {[llength [$n getBTerms]]} {return 0}
  foreach q [$n getITerms] {if {[[$q getMTerm] getIoType] eq "INPUT"} {return 0}}
 }
 return 1
}
proc nb_cd_place {inst tx ty} {
 set b [ord::get_db_block]
 set rows {};set occ [dict create]
 foreach row [$b getRows] {
  set box [$row getBBox];set y [$box yMin]
  lappend rows [list [expr {abs($y-$ty)}] $y [$box xMin] [$box xMax] [$box yMax] [$row getSpacing] [$row getOrient]]
 }
 # All current cell footprints are obstacles, not only fixed cells.
 foreach other [$b getInsts] {
  if {$other eq $inst} continue
  set box [$other getBBox]
  set y0 [expr {int(floor([$box yMin]/270.0))*270}]
  for {set y $y0} {$y<[$box yMax]} {incr y 270} {
   dict lappend occ $y [list [$box xMin] [$box xMax]]
  }
 }
 set w [[$inst getMaster] getWidth];set h [[$inst getMaster] getHeight]
 set best {};set score Inf
 foreach row [lsort -integer -index 0 $rows] {
  lassign $row dy y x0 x1 y1 pitch orient
  if {$dy>$score} break
  if {$y1-$y<$h || $pitch<=0} continue
  set intervals [list [list $x0 $x0] [list $x1 $x1]]
  if {[dict exists $occ $y]} {set intervals [concat $intervals [dict get $occ $y]]}
  set cursor $x0
  foreach span [lsort -integer -index 0 $intervals] {
   lassign $span a z
   if {$z<=$x0} continue
   if {$a>$x1} {set a $x1}
   set end [expr {min($a,$x1)}]
   if {$end-$cursor>=$w} {
    set x [expr {max($cursor,min($tx,$end-$w))}]
    set x [expr {$x0+int(ceil(double($x-$x0)/$pitch))*$pitch}]
    if {$x+$w<=$end} {
     set cost [expr {abs($x-$tx)+$dy}]
     if {$cost<$score} {set best [list $x $y $orient];set score $cost}
    }
   }
   set cursor [expr {max($cursor,$z)}]
   if {$cursor>=$x1} break
  }
 }
 if {$best eq ""} {error "BANK_CLOCK: no legal site for [$inst getName]"}
 lassign $best x y orient
 $inst setOrient $orient;$inst setLocation $x $y;$inst setPlacementStatus FIRM
 puts "BANK_CLOCK_PLACE [$inst getName] master=[[$inst getMaster] getName] x=$x y=$y orient=$orient distance=$score"
}
proc nb_cd_phase {} {
 set groups [dict create];set lo Inf;set hi -Inf
 set byname [dict create]
 foreach inst [[ord::get_db_block] getInsts] {
  dict set byname [string map {\\ {}} [$inst getName]] $inst
 }
 foreach p [all_registers -clock_pins -clock [all_clocks]] {
  set a [get_property $p arrival_max_rise]
  if {![string is double -strict $a] || $a eq "Inf" || $a eq "-Inf"} continue
  set lo [expr {min($lo,$a)}];set hi [expr {max($hi,$a)}]
  set n [get_full_name $p];set cut [string last / $n]
  set key [string map {\\ {}} [string range $n 0 [expr {$cut-1}]]]
  if {![dict exists $byname $key]} {error "BANK_CLOCK: unresolved register $n"}
  set inst [dict get $byname $key]
  set it [$inst findITerm [string range $n [expr {$cut+1}] end]]
  set net [$it getNet];set nn [$net getName]
  if {![dict exists $groups $nn]} {dict set groups $nn [list $a $a $net]}
  lassign [dict get $groups $nn] a0 a1 obj
  dict set groups $nn [list [expr {min($a0,$a)}] [expr {max($a1,$a)}] $obj]
 }
 puts "BANK_CLOCK_PHASE min=$lo max=$hi spread=[expr {$hi-$lo}]"
 return [list $lo $hi $groups]
}
proc nb_cd_reparent {} {
 set b [ord::get_db_block];set edits 0;set removed 0
 lassign [nb_cd_phase] lo hi groups
 dict for {nn rec} $groups {
  lassign $rec a0 a1 leafnet
  set out [nb_cd_driver $leafnet]
  if {$out eq ""} continue
  set leaf [$out getInst];set lname [$leaf getName]
  if {![string match clkbuf_leaf_*_clk_regs $lname]} continue
  set ain [$leaf findITerm A];set oldnet [$ain getNet];set net $oldnet
  set parent {};set rank {}
  for {set depth 0} {$depth<8} {incr depth} {
   set dr [nb_cd_driver $net]
   if {$dr eq ""} break
   set inst [$dr getInst];set name [$inst getName]
   if {[regexp {^clkbuf_([0-9]+)_.*_clk_regs$} $name -> r]} {set parent $inst;set rank $r;break}
   if {![string match wire* $name] || ![string match BUF* [[$inst getMaster] getName]]} break
   set pin [$inst findITerm A]
   if {$pin eq "" || $pin eq "NULL"} break
   set net [$pin getNet]
  }
  if {$parent eq ""} continue
  set lb [$leaf getBBox];set lx [expr {([$lb xMin]+[$lb xMax])/2}];set ly [expr {([$lb yMin]+[$lb yMax])/2}]
  set pb [$parent getBBox];set px [expr {([$pb xMin]+[$pb xMax])/2}];set py [expr {([$pb yMin]+[$pb yMax])/2}]
  set olddist [expr {abs($lx-$px)+abs($ly-$py)}]
  if {$olddist<=100000} continue
  set best {};set distance $olddist;set geomdist Inf;set geomname {}
  foreach cand [$b getInsts] {
   if {$cand eq $leaf || $cand eq $parent || [[$cand getMaster] getName] ne "BUFx24_ASAP7_75t_R"} continue
   if {![regexp {^clkbuf_([0-9]+)_.*_clk_regs$} [$cand getName] -> cr] || $cr!=$rank} continue
   set cb [$cand getBBox];set cx [expr {([$cb xMin]+[$cb xMax])/2}];set cy [expr {([$cb yMin]+[$cb yMax])/2}]
   set dist [expr {abs($cx-$lx)+abs($cy-$ly)}]
   if {$dist<$geomdist} {set geomdist $dist;set geomname [$cand getName]}
   if {$dist>80000 || $dist*2>=$olddist || $dist>=$distance} continue
   set onet [[$cand findITerm Y] getNet]
   if {$onet eq "NULL" || $onet eq "" || [$onet getSigType] ne "CLOCK"} continue
   set loads 0
   foreach it [$onet getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT"} {incr loads}}
   if {$loads>=32} continue
   set cp [get_pins -quiet "[$cand getName]/Y"]
   if {[llength $cp]!=1 || [llength [get_property $cp clocks]]!=1 || [get_full_name [lindex [get_property $cp clocks] 0]] ne "core_clk"} continue
   # Prove the candidate is not downstream of the moved leaf.
   set walk $cand;set safe 1
   for {set d 0} {$d<64} {incr d} {
    if {$walk eq $leaf} {set safe 0;break}
    set pin [$walk findITerm A]
    if {$pin eq "" || $pin eq "NULL"} break
    set dr [nb_cd_driver [$pin getNet]]
    if {$dr eq ""} break
    set walk [$dr getInst]
    if {$d==63} {set safe 0}
   }
   if {!$safe} continue
   set best $onet;set distance $dist
  }
  if {$best eq ""} {puts "BANK_CLOCK_REGION_SKIP leaf=$lname old_distance=$olddist nearest_same_level=$geomname nearest_distance=$geomdist";continue}
  if {$edits>=64} {error "BANK_CLOCK: regional reattachment budget exhausted"}
  $ain disconnect;$ain connect $best
  set_dont_touch [get_cells $lname]
  puts "BANK_CLOCK_REGION leaf=$lname old_parent=[$parent getName] new_net=[$best getName] old_distance=$olddist new_distance=$distance"
  incr edits
  # Remove only the now-private, unused noninverting wire-buffer chain.
  set net $oldnet
  for {set d 0} {$d<8} {incr d} {
   if {[llength [$net getBTerms]]} break
   set loads 0
   foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT"} {incr loads}}
   if {$loads} break
   set dr [nb_cd_driver $net]
   if {$dr eq ""} break
   set inst [$dr getInst]
   if {![string match wire* [$inst getName]] || ![string match BUF* [[$inst getMaster] getName]]} break
   set up [[$inst findITerm A] getNet]
   odb::dbInst_destroy $inst;odb::dbNet_destroy $net
   set net $up;incr removed
  }
 }
 estimate_parasitics -placement
 puts "BANK_CLOCK_REGIONS reattachments=$edits removed_private_wire_buffers=$removed"
}
proc nb_cd_run {} {
 set b [ord::get_db_block];set db [ord::get_db]
 set master [$db findMaster BUFx24_ASAP7_75t_R]
 if {$master eq "NULL" || $master eq ""} {error "BANK_CLOCK: actual BUF24 master absent"}
 if {[$master getWidth]!=1620 || [$master getHeight]!=270} {error "BANK_CLOCK: unmodeled BUF24 geometry"}
 set moves 0
 foreach inst [$b getInsts] {
  if {![[$inst getMaster] isBlock]} continue
  set pin [$inst findITerm clk]
  if {$pin eq "NULL" || $pin eq ""} continue
  set net [$pin getNet];set dr [nb_cd_driver $net]
  if {$dr eq ""} {error "BANK_CLOCK: undriven macro clock"}
  set count 0;set allmacro 1;set dummies {}
  foreach it [$net getITerms] {
   if {[[$it getMTerm] getIoType] ne "INPUT"} continue
   set li [$it getInst]
   if {[[$li getMaster] isBlock]} {incr count} elseif {[nb_cd_dummy $li]} {lappend dummies $li} else {set allmacro 0}
  }
  # Multi-macro leaves retain the CTS topology; only a singleton's long
  # delivery is localized to its real abutment pin.
  if {$count!=1 || !$allmacro} continue
  set driver [$dr getInst]
  if {[[$driver getMaster] getName] ne "BUFx24_ASAP7_75t_R"} {error "BANK_CLOCK: unexpected macro leaf cell"}
  set bb [$pin getBBox];set px [expr {([$bb xMin]+[$bb xMax])/2}];set py [expr {([$bb yMin]+[$bb yMax])/2}]
  set dbb [$driver getBBox]
  set distance [expr {abs($px-([$dbb xMin]+[$dbb xMax])/2)+abs($py-([$dbb yMin]+[$dbb yMax])/2)}]
  if {$distance>40000} {
   nb_cd_place $driver [expr {$px-[$master getWidth]-54}] [expr {$py-[$master getHeight]/2}]
   foreach dummy $dummies {
    nb_cd_place $dummy [expr {$px-[$master getWidth]-54}] [expr {$py-[$master getHeight]/2}]
   }
   incr moves
  }
 }
 set_propagated_clock [all_clocks]
 estimate_parasitics -placement
 nb_cd_reparent
 if {[info exists ::nb_cd_regions_only] && $::nb_cd_regions_only} {nb_cd_phase;return}
 set added 0
 for {set iter 0} {$iter<=32} {incr iter} {
  lassign [nb_cd_phase] lo hi groups
  if {$hi-$lo<=78.0} break
  if {$iter==32} {error "BANK_CLOCK: regional buffer budget exhausted"}
  set best {};set early Inf
  dict for {nn rec} $groups {
   lassign $rec a0 a1 net
   if {$a0>=$hi-78.0 || $a0>=$early} continue
   set eligible [expr {[llength [$net getBTerms]]==0}]
   set regloads 0;set macroloads 0
   foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set n [[$it getMTerm] getName];set li [$it getInst];set m [$li getMaster]
    if {[$m isBlock] && $n eq "clk"} {incr macroloads;continue}
    if {[nb_cd_dummy $li]} continue
    if {[string match DFF* [$m getName]] && $n eq "CLK"} {incr regloads;continue}
    set eligible 0;break
   }
   if {$regloads && $macroloads} {set eligible 0}
   if {$macroloads>2 || ($regloads+$macroloads)==0} {set eligible 0}
   if {!$eligible} continue
   set dr [nb_cd_driver $net]
   if {$dr eq "" || [[[$dr getInst] getMaster] getName] ne "BUFx24_ASAP7_75t_R"} continue
   set best [list $net $dr];set early $a0
  }
  if {$best eq ""} {error "BANK_CLOCK: no eligible fast clock-leaf branch"}
  lassign $best net dr
  set old_driver [$dr getInst];set bb [$old_driver getBBox]
  set name [format "nb_regional_phase_%02d" $added]
  if {[$b findInst $name] ne "NULL" && [$b findInst $name] ne ""} {error "BANK_CLOCK: duplicate phase buffer"}
  set buf [odb::dbInst_create $b $master $name]
  set up [odb::dbNet_create $b ${name}_input];$up setSigType CLOCK
  $dr disconnect;$dr connect $up
  [$buf findITerm A] connect $up;[$buf findITerm Y] connect $net
  nb_cd_place $buf [expr {[$bb xMax]+54}] [$bb yMin]
  set_dont_touch [get_cells $name]
  incr added
  estimate_parasitics -placement
 }
 puts "BANK_CLOCK_DELIVERY macro_driver_moves=$moves regional_buffers=$added"
}
if {![info exists ::nb_cd_definitions_only] || !$::nb_cd_definitions_only} {nb_cd_run}
