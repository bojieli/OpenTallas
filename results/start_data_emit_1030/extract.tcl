read_db /work/2_floorplan.odb
set db [ord::get_db]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /work/library.tsv w]
foreach name {BUFx8_ASAP7_75t_R BUFx2_ASAP7_75t_R INVx1_ASAP7_75t_R INVx2_ASAP7_75t_R INVx3_ASAP7_75t_R DFFHQNx1_ASAP7_75t_R DFFLQNx1_ASAP7_75t_R} {
 set master NULL
 foreach lib [$db getLibs] {set m [$lib findMaster $name]; if {$m ne "NULL"} {set master $m; break}}
 if {$master eq "NULL"} {error "actual locked library master absent: $name"}
 puts $f "CELL $name [expr {[$master getWidth]/double($u)}] [expr {[$master getHeight]/double($u)}]"
 foreach term [$master getMTerms] {
  foreach mp [$term getMPins] {foreach geom [$mp getGeometry] {
   puts $f "PIN $name [$term getName] [[$geom getTechLayer] getName] [expr {[$geom xMin]/double($u)}] [expr {[$geom yMin]/double($u)}] [expr {[$geom xMax]/double($u)}] [expr {[$geom yMax]/double($u)}]"
  }}
 }
}
close $f
