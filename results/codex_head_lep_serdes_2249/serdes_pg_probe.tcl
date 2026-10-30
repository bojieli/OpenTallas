read_db /kit/run/results/asap7/hbc_ot_s81_kp4_dchn/base/5_1_grt.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
foreach {x y} {28.1325 179.01 32.4525 19.71 105.8925 166.05 192.2925 132.57 192.2925 133.65 192.2925 136.35} {
 puts "POINT $x $y"
 foreach i [$b getInsts] {
  set r [$i getBBox]
  if {[$r xMin]>($x+1)*$u || [$r xMax]<($x-1)*$u || [$r yMin]>($y+1)*$u || [$r yMax]<($y-1)*$u} {continue}
  puts "CELL [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]"
  foreach t [$i getITerms] {set n [$t getNet]; if {$n ne "NULL"} {puts " PIN [[$t getMTerm] getName] NET [$n getName]"}}
 }
}
