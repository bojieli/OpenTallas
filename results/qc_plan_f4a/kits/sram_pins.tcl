# QC-PLAN-F4A: SRAM signal pin -> net + pin box (um) from the GRT DB, for the M4/M6 escape check (escape_check.py)
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[$b getTech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  foreach it [$i getITerms] {
    if {[$it getSigType] ne "SIGNAL"} continue
    set n [$it getNet]; if {$n eq "NULL"} continue
    foreach mp [[$it getMTerm] getMPins] {
      foreach bx [$mp getGeometry] {
        set t [$i getTransform]
        set r [odb::Rect]
        $r init [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]
        $t apply $r
        puts $f [format "%s %s %s %s %.4f %.4f %.4f %.4f" [$i getName] [[$it getMTerm] getName] [$n getName] [[$bx getTechLayer] getName] \
          [expr [$r xMin]*1.0/$u] [expr [$r yMin]*1.0/$u] [expr [$r xMax]*1.0/$u] [expr [$r yMax]*1.0/$u]]
      }
    }
  }
}
# PG straps over the macros (special wires), for the report
foreach n [$b getNets] {
  if {[$n getSigType] ni {POWER GROUND}} continue
  foreach sw [$n getSWires] { foreach w [$sw getWires] {
    set l [[$w getTechLayer] getName]; if {$l ni {M4 M5 M6}} continue
    puts $f [format "STRAP %s %s %.4f %.4f %.4f %.4f" [$n getName] $l [expr [$w xMin]*1.0/$u] [expr [$w yMin]*1.0/$u] [expr [$w xMax]*1.0/$u] [expr [$w yMax]*1.0/$u]]
  } }
}
close $f
puts "SRAM_PINS done"
