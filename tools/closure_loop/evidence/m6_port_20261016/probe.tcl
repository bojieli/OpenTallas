read_db /input/6_final.odb
set ::ot_m6_stub_um 0.384
set b [ord::get_db_block]
set initial [llength [$b getObstructions]]
foreach mode {add add remove remove} {
  set ::ot_m6_pin_access_mode $mode
  source /probe/m6_pin_access.tcl
  if {$mode eq "add"} {
    set bad 0; set good 0
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M6"} continue
      if {[$r xMin] <= 60 && 60 <= [$r xMax] && [$r yMin] < 68560 && 68560 < [$r yMax]} {incr bad}
      if {[$r xMin] < 192 && 192 < [$r xMax] && [$r yMin] < 41936 && 41936 < [$r yMax]} {incr good}
    }
    puts "M6_COMPLEMENT outside_terminal_blocked=$bad legal_terminal_blocked=$good"
    if {!$bad || $good} {error "M6 complement geometry mismatch"}
  }
  puts "M6_IDEMPOTENCE $mode [expr {[llength [$b getObstructions]]-$initial}]"
}
write_abstract_lef /probe/actual.lef
write_def /probe/actual.def
file copy -force /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef /probe/tech.lef
# In a copied native DB, encode a signal route through the unprotected M6
# interior. This is a counterexample to the former cap-only ECO acceptance.
set nt [$b findNet {wo_d[0]}]
if {$nt eq "NULL"} {error "missing fixture net"}
set wr [$nt getWire]
if {$wr ne "NULL"} {odb::dbWire_destroy $wr}
set wr [odb::dbWire_create $nt]
set enc [odb::dbWireEncoder]
$enc begin $wr
$enc newPath [[ord::get_db_tech] findLayer M6] ROUTED
$enc addPoint 10000 10000
$enc addPoint 20000 10000
$enc end
write_def /probe/interior.def
puts "M6_NATIVE_COUNTEREXAMPLE complete"
# Small native positive: preserve actual terminals/tech, retain one signal
# rectangle wholly in its own BPin. This is a geometry-audit fixture, not PPA.
foreach n [$b getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set w [$n getWire]; if {$w ne "NULL"} {odb::dbWire_destroy $w}
}
foreach o [$b getObstructions] {
  if {[[[$o getBBox] getTechLayer] getRoutingLevel] > 5} {odb::dbObstruction_destroy $o}
}
set bt [$b findBTerm {wo_d[0]}]
set bx [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
set y [expr {([$bx yMin]+[$bx yMax])/2}]
set nt [$bt getNet]
set wr [odb::dbWire_create $nt]
set enc [odb::dbWireEncoder]; $enc begin $wr
$enc newPath [[ord::get_db_tech] findLayer M6] ROUTED
$enc addPoint [expr {[$bx xMin]+32}] $y
$enc addPoint [expr {[$bx xMax]-32}] $y
$enc end
write_def /probe/positive.def
puts "M6_NATIVE_POSITIVE complete"
