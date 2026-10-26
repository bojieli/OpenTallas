# Assign anonymous combinational logic to the zone of its downstream data endpoints.
# All ownership is physical metadata; the netlist and clock-cycle behavior are unchanged.
proc ot_zone_members {blk spec} {
  set labels [dict create]; set todo [dict create]; set ids [dict create]
  foreach inst [$blk getInsts] {
    if {![[$inst getMaster] isCore] || [$inst getPlacementStatus] in {FIRM LOCKED}} continue
    set name [$inst getName]; dict set ids $inst $name
    set assigned 0
    foreach {zn rx x0 y0 x1 y1} $spec {
      if {[regexp $rx $name]} {dict set labels $inst $zn; set assigned 1; break}
    }
    if {!$assigned} {dict set todo $inst 1}
  }
  # Build data edges once. High-fanout broadcast nets (clock/reset/control) do not
  # identify a local cone. Prefer backward propagation from downstream endpoints.
  set backward [dict create]; set forward [dict create]
  foreach net [$blk getNets] {
    if {[$net getSigType] in {POWER GROUND CLOCK}} continue
    set terms [$net getITerms]
    if {[llength $terms] > 65} continue
    set drivers {}; set loads {}
    foreach term $terms {
      set inst [$term getInst]
      if {![dict exists $ids $inst]} continue
      if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $inst} else {lappend loads $inst}
    }
    foreach d $drivers {foreach l $loads {if {$d ne $l} {dict lappend backward $d $l; dict lappend forward $l $d}}}
  }
  foreach edges [list $backward $forward] {
    for {set round 0} {$round < 100 && [dict size $todo]} {incr round} {
      set found [dict create]
      dict for {inst unused} $todo {
        if {![dict exists $edges $inst]} continue
        set votes [dict create]
        foreach other [dict get $edges $inst] {
          if {[dict exists $labels $other]} {dict incr votes [dict get $labels $other]}
        }
        set winner {}; set best 0; set tie 0
        dict for {zn n} $votes {
          if {$n > $best} {set winner $zn; set best $n; set tie 0} elseif {$n == $best} {set tie 1}
        }
        if {$best && !$tie} {dict set found $inst $winner}
      }
      if {![dict size $found]} break
      dict for {inst zn} $found {dict set labels $inst $zn; dict unset todo $inst}
    }
  }
  # Disconnected/shared controls belong to the controller band, never to an
  # unaccounted-for top-level sliver. Membership coverage is checked below.
  puts "OT_ZONE_MEMBERS controller/shared remainder [dict size $todo]"
  dict for {inst unused} $todo {dict set labels $inst ctl}
  if {[dict size $labels] != [dict size $ids]} {error "OT_ZONE_MEMBERS incomplete ownership"}
  return $labels
}
