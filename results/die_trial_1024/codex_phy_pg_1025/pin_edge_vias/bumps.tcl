set block [ord::get_db_block]
set m9 [[ord::get_db_tech] findLayer M9]
set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bump_shapes {}
set bump_x_cache {}
foreach net_name {VDD VSS} {
  set shapes {}
  foreach wire [[$block findNet $net_name] getSWires] {
    foreach shape [$wire getWires] {
      if {[$shape isVia] || [$shape getTechLayer] ne $m9} continue
      lappend shapes [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]
    }
  }
  if {![llength $shapes]} { error "no actual M9 metal for $net_name voltage sources" }
  dict set bump_shapes $net_name $shapes
}
set bx [expr {43.2*$bump_dbu}]; set by [expr {43.2*$bump_dbu}]
set cache_key [list VDD $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDD] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDD] VDD_core_b0]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {193.2*$bump_dbu}]; set by [expr {43.2*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_core_b1]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {343.2*$bump_dbu}]; set by [expr {43.2*$bump_dbu}]
set cache_key [list VDD $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDD] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDD] VDD_core_b2]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
puts "OT_BUMPS actual_m9_sources 3 cached_columns [dict size $bump_x_cache]"
set block [ord::get_db_block]
set m9 [[ord::get_db_tech] findLayer M9]
set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bump_shapes {}
set bump_x_cache {}
foreach net_name {VDDPHY VSS} {
  set shapes {}
  foreach wire [[$block findNet $net_name] getSWires] {
    foreach shape [$wire getWires] {
      if {[$shape isVia] || [$shape getTechLayer] ne $m9} continue
      lappend shapes [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]
    }
  }
  if {![llength $shapes]} { error "no actual M9 metal for $net_name voltage sources" }
  dict set bump_shapes $net_name $shapes
}
set bx [expr {22.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b0]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {22.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b1]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {22.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b2]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {22.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b3]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {22.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b4]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {22.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b5]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b6]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b7]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b8]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b9]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b10]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {67.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b11]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b12]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b13]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b14]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b15]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b16]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {112.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b17]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b18]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b19]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b20]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b21]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b22]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {157.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b23]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b24]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b25]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b26]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b27]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b28]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {202.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b29]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b30]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b31]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b32]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b33]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b34]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {247.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b35]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b36]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b37]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b38]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b39]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b40]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {292.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b41]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {108.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b42]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {153.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b43]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {198.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b44]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {243.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b45]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {288.9*$bump_dbu}]
set cache_key [list VSS $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VSS] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VSS] VSS_phy_b46]; $bt setIoType INOUT; $bt setSigType GROUND; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
set bx [expr {337.5*$bump_dbu}]; set by [expr {333.9*$bump_dbu}]
set cache_key [list VDDPHY $bx]
if {![dict exists $bump_x_cache $cache_key]} {
  set nearest {}; set x_distance 1e30
  foreach rect [dict get $bump_shapes VDDPHY] {
    lassign $rect x0 y0 x1 y1
    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]
    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }
  }
  dict set bump_x_cache $cache_key $nearest
}
set best {}; set best_distance 1e30
foreach rect [dict get $bump_x_cache $cache_key] {
  lassign $rect x0 y0 x1 y1
  set cx [expr {($x0+$x1)/2.0}]
  set half [expr {min(4*$bump_dbu/2.0,($y1-$y0)/2.0)}]
  set cy [expr {max($y0+$half,min($y1-$half,$by))}]
  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]
  if {$distance < $best_distance} {
    set best_distance $distance
    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]
  }
}
set bt [odb::dbBTerm_create [$block findNet VDDPHY] VDDPHY_phy_b47]; $bt setIoType INOUT; $bt setSigType POWER; set bp [odb::dbBPin_create $bt]
odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM
puts "OT_BUMPS actual_m9_sources 48 cached_columns [dict size $bump_x_cache]"
