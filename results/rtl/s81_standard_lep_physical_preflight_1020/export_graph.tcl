# Read-only exact native graph after pin/macro planning. No placement algorithm.
set variant $::env(OT_LEP_VARIANT)
read_db /run/physical_preflight/$variant/floorplan.odb
set b [ord::get_db_block]
set f [open /run/physical_preflight/$variant/native_graph.tsv w]
puts $f "net\tkind\tinstance\tmaster\tpin\tdirection\trole"
foreach net [$b getNets] {
  set nn [$net getName]
  foreach t [$net getITerms] {
    set i [$t getInst];set m [$i getMaster];set mt [$t getMTerm]
    puts $f [join [list $nn cell [$i getName] [$m getName] [$mt getName] [$mt getIoType] [$mt getSigType]] "\t"]
  }
  foreach t [$net getBTerms] {
    puts $f [join [list $nn port {} {} [$t getName] [$t getIoType] [$t getSigType]] "\t"]
  }
}
close $f
set f [open /run/physical_preflight/$variant/macro_terminals.tsv w]
puts $f "net\tinstance\tpin\tx0_um\ty0_um\tx1_um\ty1_um"
set unit [expr {double([$b getDbUnitsPerMicron])}]
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 if {[$i getOrient] ne "R0"} {error {LEP_MODEL supports actualR0 only}}
 lassign [$i getLocation] ox oy
 foreach t [$i getITerms] {
  set net [$t getNet]
  if {$net eq "NULL"} {continue}
  set xmin Inf;set ymin Inf;set xmax -Inf;set ymax -Inf
  foreach mp [[$t getMTerm] getMPins] {
   foreach q [$mp getGeometry] {
    set xmin [expr {min($xmin,[$q xMin])}];set ymin [expr {min($ymin,[$q yMin])}]
    set xmax [expr {max($xmax,[$q xMax])}];set ymax [expr {max($ymax,[$q yMax])}]
   }
  }
  if {$xmin eq "Inf"} {error "missing native macro terminal [$i getName]/[[$t getMTerm] getName]"}
  puts $f [join [list [$net getName] [$i getName] [[$t getMTerm] getName] [expr {($xmin+$ox)/$unit}] [expr {($ymin+$oy)/$unit}] [expr {($xmax+$ox)/$unit}] [expr {($ymax+$oy)/$unit}]] "\t"]
 }
}
close $f
set f [open /run/physical_preflight/$variant/tracks.tsv w]
foreach grid [$b getTrackGrids] {
  set l [$grid getTechLayer]
  puts $f [join [list [$l getName] [$l getDirection] [join [$grid getGridX] ,] [join [$grid getGridY] ,]] "\t"]
}
close $f
puts "LEP_NATIVE_GRAPH_EXPORTED $variant"
