# Explicit physical profile: upper-metal trunk NDR, normal local/pin-access
# wiring. No timing constraint, placement, connectivity, or cell changes.
namespace eval ot_upper_trunk {}
proc ot_upper_trunk::apply {block clock_names root_name expected_trunk expected_local} {
  set clocks [dict create]
  foreach name $clock_names {dict set clocks $name 1}
  set trunks {}; set locals {}; set topology {}; set placement {}
  foreach inst [$block getInsts] {
    dict set placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName] [$inst getPlacementStatus] [$inst isDoNotTouch]]
  }
  foreach net [$block getNets] {
    set name [$net getName]; set rule [$net getNonDefaultRule]
    set rule_name [expr {$rule eq "NULL" ? "DEFAULT" : [$rule getName]}]
    if {$name eq $root_name || [regexp {^ot_dtsh_[0-9]+_Y$} $name]} {
      if {![dict exists $clocks $name] || $rule_name ne "ot_dtsh_4w2s"} {error "Upper trunk profile: undeclared trunk/rule $name $rule_name"}
      lappend trunks $net
    } elseif {$rule_name eq "CTS_NDR_0"} {
      if {![dict exists $clocks $name]} {error "Upper trunk profile refuses nonclock CTS NDR net $name"}
      lappend locals $net
    }
    set terms {}
    foreach it [$net getITerms] {lappend terms "[[$it getInst] getName]/[[$it getMTerm] getName]"}
    dict set topology $name [lsort $terms]
  }
  if {[llength $trunks] != $expected_trunk || [llength $locals] != $expected_local} {
    error "Upper trunk profile: unexpected ownership [llength $trunks]/[llength $locals], expected $expected_trunk/$expected_local"
  }
  set tech [[ord::get_db] getTech]
  set dbu [$block getDbUnitsPerMicron]
  set widths {}; set spacings {}
  foreach name {M1 M2 M3 M4 M5 M6 M7 M8 M9} {
    set layer [$tech findLayer $name]
    if {$layer eq "NULL"} {error "Upper trunk profile missing layer $name"}
    set w [expr {double([$layer getWidth])/$dbu}]
    set s [expr {double([$layer getSpacing])/$dbu}]
    if {$name in {M6 M7}} {set w [expr {4*$w}]; set s [expr {2*$s}]}
    lappend widths $name $w; lappend spacings $name $s
  }
  set name ot_upper_trunk_4w2s
  if {[$block findNonDefaultRule $name] ne "NULL"} {error "Upper trunk profile already applied"}
  create_ndr -name $name -width $widths -spacing $spacings
  set rule [$block findNonDefaultRule $name]
  if {$rule eq "NULL"} {error "Upper trunk profile NDR creation failed"}
  foreach group [list [list $trunks $rule] [list $locals NULL]] {
    lassign $group nets target
    foreach net $nets {
      set protected [$net isDoNotTouch]
      if {$protected} {$net setDoNotTouch false}
      set failed [catch {$net setNonDefaultRule $target} message]
      if {$protected} {$net setDoNotTouch true}
      if {$failed} {error $message}
    }
  }
  foreach net [$block getNets] {
    set terms {}
    foreach it [$net getITerms] {lappend terms "[[$it getInst] getName]/[[$it getMTerm] getName]"}
    if {[lsort $terms] ne [dict get $topology [$net getName]]} {error "Upper trunk profile changed connectivity"}
  }
  foreach inst [$block getInsts] {
    set got [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName] [$inst getPlacementStatus] [$inst isDoNotTouch]]
    if {$got ne [dict get $placement [$inst getName]]} {error "Upper trunk profile changed instance [$inst getName]"}
  }
  puts "UPPER_TRUNK_PROFILE PASS trunk=[llength $trunks] local_default=[llength $locals] wide_layers=M6,M7 no_clock_or_cell_or_constraint_change=1"
}
