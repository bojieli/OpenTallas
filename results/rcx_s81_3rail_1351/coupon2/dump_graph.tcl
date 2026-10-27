read_db /out/extracted.odb
set n [[ord::get_db_block] findNet ck_mesh]
set w [$n getWire]
set f [open /out/db_graph.tsv w]
set d [odb::dbWireDecoder]
$d begin $w
set x 0; set y 0
while {1} {
 set op [$d next]
 if {$op == 12} break
 if {$op == 4 || $op == 5} {set pt [$d getPoint];set x [lindex $pt 0];set y [lindex $pt 1]}
 if {$op in {4 5 6 7}} {
  puts $f "J [$d getJunctionId] [[$d getLayer] getName] $x $y"
 }
}
foreach c [$n getCapNodes] {
 set label "I";set term "-"
 if {[$c isBTerm]} {set label B;set term [[$c getBTerm] getName]}
 puts $f "C [$c getId] [$c getNode] $label $term"
}
close $f
