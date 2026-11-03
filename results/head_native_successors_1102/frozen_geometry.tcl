# Read-only guards shared by two ROOT-held private successor preparations.
# Deliberately excludes routing guides: a capacity diagnostic may create them.
proc hg_box {b} { return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
proc hg_state {{omit_pose ""}} {
 set b [ord::get_db_block]
 set poses {}; set nets {}; set ports {}; set pg {}; set masters {}
 foreach i [$b getInsts] {
  set m [$i getMaster]; dict set masters [$m getName] $m
  if {[$i getName] ne $omit_pose} {lappend poses [list [$i getName] [$m getName] [$i getOrient] [$i getLocation] [$i getPlacementStatus] [$i isDoNotTouch] [hg_box [$i getBBox]]]}
 }
 foreach n [$b getNets] {
  set ends {}
  foreach t [$n getITerms] {lappend ends [list I [[$t getInst] getName] [[$t getMTerm] getName]]}
  foreach t [$n getBTerms] {lappend ends [list B [$t getName]]}
  lappend nets [list [$n getName] [$n getSigType] [$n isSpecial] [lsort $ends]]
  if {[$n getSigType] in {POWER GROUND}} {
   foreach sw [$n getSWires] {foreach w [$sw getWires] {
    set layer VIA
    if {![$w isVia]} {set layer [[$w getTechLayer] getName]}
    lappend pg [list [$n getName] [$w isVia] $layer [hg_box $w]]
   }}
  }
 }
 foreach t [$b getBTerms] {foreach p [$t getBPins] {foreach q [$p getBoxes] {lappend ports [list [$t getName] [$t getIoType] [$t getSigType] [[$q getTechLayer] getName] [hg_box $q]]}}}
 set pin_shapes {}
 dict for {name m} $masters {
  foreach t [$m getMTerms] {foreach p [$t getMPins] {foreach q [$p getGeometry] {
   if {[$q isVia]} {error "HG native master pin via not supported by frozen-shape guard: $name"}
   lappend pin_shapes [list $name [$t getName] [$t getIoType] [$t getSigType] [[$q getTechLayer] getName] [hg_box $q]]
  }}}
 }
 return [list [lsort $poses] [lsort $nets] [lsort $ports] [lsort $pg] [lsort $pin_shapes]]
}
proc hg_require_same {before after} {
 foreach label {all_other_instances connections_and_classes ports_roots pg_geometry master_pin_geometry} a $before b $after {
  if {$a ne $b} {error "HG_FROZEN_DELTA $label"}
 }
 puts "HG_FROZEN guards PASS (all other bodies/TAPs/clock poses/status/DNT, ports/roots, graph, PG and master pins)"
}
proc hg_write {path state} {
 set f [open $path w]; foreach label {poses nets ports pg master_pins} rows $state {puts $f [list $label $rows]}; close $f
}
