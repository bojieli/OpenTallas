# Exact flat-forest ownership. Every sequential clock pin is named; every
# planned driver is a native buffer with a frozen origin and root identity.
proc ot_flat_no_macros {} {
  foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] isBlock]} {error "OT_FLAT actual native macro is unsupported [$inst getName]"}
  }
}
proc ot_flat_clock_sources {} {
  set b [ord::get_db_block];set found {};set primary ""
  foreach clock [all_clocks] {
    foreach source [get_property $clock sources] {
      set name [get_full_name $source];set bt [$b findBTerm $name]
      if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} continue
      if {![dict exists $::ot_flat_roots $name]} {error "OT_FLAT undeclared STA input clock $name"}
      dict lappend found $name $clock
    }
  }
  dict for {root spec} $::ot_flat_roots {
    if {![dict exists $found $root] || [llength [lsort -unique [dict get $found $root]]]!=1} {error "OT_FLAT missing/ambiguous STA clock source $root"}
    if {[lindex $spec 0] eq "primary"} {
      set clock [lindex [dict get $found $root] 0]
      if {$primary ne "" && $clock ne $primary} {error "OT_FLAT primary taps are not one declared STA clock"}
      set primary $clock
    }
  }
}
proc ot_flat_input_nets {} {
  set b [ord::get_db_block]
  dict for {root spec} $::ot_flat_roots {
    set bt [$b findBTerm $root];set n [$bt getNet]
    if {$n eq "NULL" || $n eq ""} {set n [odb::dbNet_create $b ${root}_flat_input];$bt connect $n}
    $n setSigType CLOCK
  }
}
proc ot_flat_native_guard {} {
  ot_flat_no_macros
  ot_flat_clock_sources
  set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set rootnets {};set existing 0
  dict for {name spec} $::ot_flat_cells {if {[$b findInst $name] ne "NULL"} {incr existing}}
  if {$existing} {
    if {$existing != [dict size $::ot_flat_cells]} {error "OT_FLAT partial previous forest"}
    ot_flat_graph_guard
    return
  }
  dict for {root spec} $::ot_flat_roots {
    lassign $spec role node x y
    set bt [$b findBTerm $root]
    if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} {error "OT_FLAT missing input $root"}
    set box [$bt getBBox]
    if {abs(([$box xMin]+[$box xMax])/2.0/$u-$x)>0.001 || abs(([$box yMin]+[$box yMax])/2.0/$u-$y)>0.001} {error "OT_FLAT stale input pin $root"}
    set n [$bt getNet]
    if {$n ne "NULL" && $n ne ""} {
      if {[dict exists $rootnets $n]} {error "OT_FLAT aliased input roots $root"}
      dict set rootnets $n $root
    }
  }
  set seen {}
  foreach p [all_registers -clock_pins] {
    set it [sta::sta_to_db_pin $p]
    if {$it eq "NULL" || $it eq ""} {error "OT_FLAT unmapped clock pin"}
    set inst [$it getInst];set name [$inst getName]
    if {![dict exists $::ot_flat_sinks $name]} {error "OT_FLAT unlisted native clock $name"}
    lassign [dict get $::ot_flat_sinks $name] target source master pin x y
    if {[[ $inst getMaster] getName] ne $master || [[$it getMTerm] getName] ne $pin} {error "OT_FLAT stale native clock master/pin $name"}
    set box [$inst getBBox]
    if {abs(([$box xMin]+[$box xMax])/2.0/$u-$x)>0.001 || abs(([$box yMin]+[$box yMax])/2.0/$u-$y)>0.001} {error "OT_FLAT stale native sink geometry $name"}
    set net [$it getNet]
    if {![dict exists $rootnets $net]} {error "OT_FLAT original clock not a declared direct input $name"}
    set actual [dict get $rootnets $net]
    set role [lindex [dict get $::ot_flat_roots $target] 0]
    if {$role eq "forwarded" && $actual ne $source} {error "OT_FLAT forwarded root stealing $name"}
    if {$role eq "primary" && ![regexp {^clk(_t[0-9]+)?$} $actual]} {error "OT_FLAT primary root stealing $name"}
    if {[dict exists $seen $name]} {error "OT_FLAT duplicate native clock pin $name"}
    dict set seen $name 1
  }
  if {[dict size $seen]!=[dict size $::ot_flat_sinks]} {error "OT_FLAT missing native clock inventory"}
  dict for {net root} $rootnets {
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set name [[$it getInst] getName]
      if {![dict exists $seen $name] || [[$it getMTerm] getName] ne "CLK"} {error "OT_FLAT unmodeled native root load $root $name/[[$it getMTerm] getName]"}
    }
  }
  # This post-place recovery inserts into actual empty legal sites. It never
  # assumes that an occupied movable logic site is a reserved clock island.
  set pitch [[[lindex [$b getRows] 0] getSite] getHeight]
  set occupied {}
  foreach inst [$b getInsts] {
    if {[$inst getPlacementStatus] in {NONE UNPLACED}} continue
    set box [$inst getBBox]
    for {set row [expr {int(floor([$box yMin]/double($pitch)))}]} {$row*$pitch<[$box yMax]} {incr row} {
      dict lappend occupied $row [list [$inst getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
    }
  }
  # Check real row/site legality and hard blockages before any inserted cell.
  dict for {name spec} $::ot_flat_cells {
    lassign $spec master parent root ox oy cx cy orient w h
    set m [[ord::get_db] findMaster $master]
    if {$m eq "NULL" || abs([$m getWidth]/double($u)-$w)>0.001 || abs([$m getHeight]/double($u)-$h)>0.001} {error "OT_FLAT stale driver footprint $name"}
    set X [expr {round($ox*$u)}];set Y [expr {round($oy*$u)}];set W [$m getWidth];set H [$m getHeight];set legal 0
    foreach row [$b getRows] {
      lassign [$row getOrigin] rx ry;set site [$row getSite];set rb [$row getBBox]
      if {$Y==$ry && $X>=$rx && $X+$W<=[$rb xMax] && $H==[$site getHeight] && ($X-$rx)%[$site getWidth]==0 && [$row getOrient] eq $orient} {set legal 1;break}
    }
    if {!$legal} {error "OT_FLAT driver not a legal frozen row site $name"}
    set row [expr {int(floor($Y/double($pitch)))}]
    if {[dict exists $occupied $row]} {
      foreach obstacle [dict get $occupied $row] {
        lassign $obstacle other x0 y0 x1 y1
        if {$X<$x1 && $x0<$X+$W && $Y<$y1 && $y0<$Y+$H} {error "OT_FLAT insertion site occupied $name by $other"}
      }
    }
    foreach block [$b getBlockages] {
      if {[$block isSoft] || [$block getMaxDensity]>0} continue
      set box [$block getBBox]
      if {$X<[$box xMax] && [$box xMin]<$X+$W && $Y<[$box yMax] && [$box yMin]<$Y+$H} {error "OT_FLAT driver in hard blockage $name"}
    }
  }
  puts "OT_FLAT native_inventory=[dict size $seen] declared_roots=[dict size $::ot_flat_roots]"
}
proc ot_flat_graph_guard {} {
  ot_flat_no_macros
  ot_flat_clock_sources
  set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set expected {};set nets {}
  dict for {root spec} $::ot_flat_roots {
    lassign $spec role node x y;set bt [$b findBTerm $root]
    if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} {error "OT_FLAT root disappeared $root"}
    set box [$bt getBBox]
    if {abs(([$box xMin]+[$box xMax])/2.0/$u-$x)>0.001 || abs(([$box yMin]+[$box yMax])/2.0/$u-$y)>0.001} {error "OT_FLAT input pin moved $root"}
    dict set nets port:$root [$bt getNet]
  }
  dict for {name spec} $::ot_flat_cells {
    lassign $spec master parent root ox oy cx cy orient
    set i [$b findInst $name]
    if {$i eq "NULL" || [[$i getMaster] getName] ne $master || ![$i isDoNotTouch]} {error "OT_FLAT driver changed $name"}
    lassign [$i getLocation] x y
    if {$x!=round($ox*$u) || $y!=round($oy*$u) || [$i getOrient] ne $orient} {error "OT_FLAT driver moved $name"}
    set out [[$i findITerm Y] getNet]
    if {$out eq "NULL" || ![$out isDoNotTouch] || [$out getSigType] ne "CLOCK"} {error "OT_FLAT unprotected driver net $name"}
    dict set nets $name $out
    dict lappend expected $parent $name/A
  }
  dict for {name spec} $::ot_flat_sinks {
    lassign $spec root source master pin x y owner
    set inst [$b findInst $name]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master} {error "OT_FLAT sink changed $name"}
    set box [$inst getBBox]
    if {abs(([$box xMin]+[$box xMax])/2.0/$u-$x)>0.001 || abs(([$box yMin]+[$box yMax])/2.0/$u-$y)>0.001} {error "OT_FLAT modeled sink moved $name"}
    set net [[$inst findITerm $pin] getNet]
    if {$net ne [dict get $nets $owner] || [lindex [dict get $::ot_flat_cells $owner] 2] ne $root} {error "OT_FLAT exact sink leaf changed $name"}
    dict lappend expected $owner $name/$pin
  }
  set seen_nets {}
  dict for {node net} $nets {
    if {$net eq "NULL"} {error "OT_FLAT null tree net $node"}
    if {[dict exists $seen_nets $net]} {error "OT_FLAT aliased tree nets $node"}
    dict set seen_nets $net $node
    set actual {};set drivers {}
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers "[[$it getInst] getName]/[[$it getMTerm] getName]"}
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      lappend actual "[[$it getInst] getName]/[[$it getMTerm] getName]"
    }
    set want [expr {[dict exists $expected $node] ? [dict get $expected $node] : {}}]
    if {[lsort $actual] ne [lsort $want]} {error "OT_FLAT clock graph edited at $node"}
    if {![string match port:* $node] && $drivers ne [list $node/Y]} {error "OT_FLAT clock driver edited at $node"}
    if {[string match port:* $node] && [llength $drivers]} {error "OT_FLAT input root has an internal driver $node"}
  }
  puts "OT_FLAT planned_graph_preserved roots=[dict size $::ot_flat_roots] cells=[dict size $::ot_flat_cells] sinks=[dict size $::ot_flat_sinks]"
}
