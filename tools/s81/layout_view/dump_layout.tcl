# Dump placement geometry of an ODB for tools/s81/layout_view/render_layout.py:
#   openroad -exit -no_init dump_layout.tcl  (env ODB, OUT)
read_db $::env(ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set f [open $::env(OUT) w]
set die [$block getDieArea]
puts $f "DIE [expr {[$die xMin]/double($dbu)}] [expr {[$die yMin]/double($dbu)}] [expr {[$die xMax]/double($dbu)}] [expr {[$die yMax]/double($dbu)}]"
foreach inst [$block getInsts] {
  set m [$inst getMaster]; set mn [$m getName]
  if {[string match "TAPCELL*" $mn] || [string match "FILLER*" $mn] || [string match "DECAP*" $mn]} continue
  set bb [$inst getBBox]
  set cls std
  if {[$m isBlock]} {set cls macro} elseif {[regexp {^ICG} $mn]} {set cls icg} elseif {[regexp {^(DFF|SDF|ASYNC)} $mn]} {set cls ff} elseif {[regexp {^(DHL|DLL)} $mn]} {set cls latch} elseif {[regexp {^(BUF|CKINV|INV)} $mn] && [regexp {clkbuf|clkload|cts} [$inst getName]]} {set cls clkbuf} elseif {[regexp {^(HB)} $mn]} {set cls hold}
  puts $f "I $cls [expr {[$bb xMin]/double($dbu)}] [expr {[$bb yMin]/double($dbu)}] [expr {[$bb xMax]/double($dbu)}] [expr {[$bb yMax]/double($dbu)}] [$inst getName]"
}
foreach bt [$block getBTerms] {
  set n [$bt getName]
  foreach bp [$bt getBPins] { foreach box [$bp getBoxes] {
    puts $f "P [expr {([$box xMin]+[$box xMax])/2.0/$dbu}] [expr {([$box yMin]+[$box yMax])/2.0/$dbu}] [$bt getSigType] $n"
  } }
}
close $f
