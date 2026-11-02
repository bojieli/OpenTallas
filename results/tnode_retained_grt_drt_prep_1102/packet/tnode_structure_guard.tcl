# Compare all logical data/CLOCK structure, pin geometry, masters/poses/flags.
# Deliberately exclude only routed wire geometry, which DRT is allowed to change.
proc tnode_structure_guard {b} {
  set instances {}; set nets {}; set connectivity {}; set terms {}
  foreach i [$b getInsts] {
    lappend instances [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrigin] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [$i getSourceType]]
    foreach t [$i getITerms] {
      if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue
      set n [$t getNet]; set name NULL
      if {$n ne "NULL"} {set name [$n getName]}
      lappend connectivity [list [$i getName] [[$t getMTerm] getName] [[$t getMTerm] getSigType] [[$t getMTerm] getIoType] $name]
    }
  }
  foreach n [$b getNets] {
    set ndr [$n getNonDefaultRule]; set ndr_name NULL
    if {$ndr ne "NULL"} {set ndr_name [$ndr getName]}
    lappend nets [list [$n getName] [$n getSigType] [$n isSpecial] [$n isDoNotTouch] $ndr_name]
  }
  foreach t [$b getBTerms] {
    set n [$t getNet]; set name NULL
    if {$n ne "NULL"} {set name [$n getName]}
    set pins {}
    foreach p [$t getBPins] {
      set boxes {}
      foreach box [$p getBoxes] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
      lappend pins [list [$p getPlacementStatus] [lsort $boxes]]
    }
    lappend terms [list [$t getName] [$t getSigType] [$t getIoType] $name [lsort $pins]]
  }
  return [dict create instances [lsort $instances] net_flags [lsort $nets] data_clock_connectivity [lsort $connectivity] bterm_geometry [lsort $terms]]
}
