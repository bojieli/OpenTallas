set rootdir /work
set files [glob $rootdir/results/asap7/*/base/3_5_place_dp.odb]
read_db [lindex $files 0]
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
array set memo {}
proc clkroot {net {depth 0}} {
 global memo
 set key [$net getId]
 if {[info exists memo($key)]} {return $memo($key)}
 foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {set memo($key) [$bt getName];return $memo($key)}}
 if {$depth>50} {return depth_limit}
 foreach it [$net getITerms] {
  if {[$it getIoType] ne "OUTPUT"} {continue}
  set inst [$it getInst]
  foreach input {A CLK CK} {
   set p [$inst findITerm $input]
   if {$p ne "NULL" && [$p getNet] ne "NULL"} {set memo($key) [clkroot [$p getNet] [expr {$depth+1}]];return $memo($key)}
  }
  return "logic:[$inst getName]"
 }
 return undriven
}
set f [open $rootdir/sink_ownership_odb_2115.tsv w]
puts $f "root\tcell\tmaster\tx_um\ty_um"
set counts [dict create]
foreach inst [$blk getInsts] {
 set master [$inst getMaster]
 if {![regexp {DFF} [$master getName]]} {continue}
 set cp [$inst findITerm CLK]
 if {$cp eq "NULL" || [$cp getNet] eq "NULL"} {continue}
 set root [clkroot [$cp getNet]]
 dict incr counts $root
 set bb [$inst getBBox]
 puts $f "$root\t[$inst getName]\t[$master getName]\t[expr {double([$bb xMin])/$dbu}]\t[expr {double([$bb yMin])/$dbu}]"
}
close $f
puts "SINK_OWNERSHIP_COUNTS $counts"
exit
