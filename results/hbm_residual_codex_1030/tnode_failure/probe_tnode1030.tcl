read_db /work/run/results/asap7/hbc_ot_hnx_fused_tnode/base/5_1_grt.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set n [$b findNet mp_isl0_ck_i]
puts "PROBE units=$u net=[$n getName]"
foreach t [$n getBTerms] {foreach p [$t getBPins] {foreach q [$p getBoxes] {puts "BPIN [$t getName] [[$q getTechLayer] getName] [$q xMin] [$q yMin] [$q xMax] [$q yMax]"}}}
foreach it [$n getITerms] {set i [$it getInst];puts "ITERM [$i getName]/[[$it getMTerm] getName] master=[[$i getMaster] getName] orient=[$i getOrient] loc=[$i getLocation] bbox=[[$i getBBox] xMin],[[$i getBBox] yMin],[[$i getBBox] xMax],[[$i getBBox] yMax]"}
set X0 [expr {84.8*$u}];set X1 [expr {85.8*$u}];set Y0 [expr {88.0*$u}];set Y1 [expr {89.1*$u}]
foreach name {VDD VSS} {set pg [$b findNet $name];foreach sw [$pg getSWires] {foreach q [$sw getWires] {
 if {[$q xMin]<$X1 && [$q xMax]>$X0 && [$q yMin]<$Y1 && [$q yMax]>$Y0} {
  set l [$q getTechLayer];set layer VIA;if {$l ne "NULL"} {set layer [$l getName]}
  puts "PG $name $layer via=[$q isVia] [$q xMin] [$q yMin] [$q xMax] [$q yMax]"
 }
}}}
exit
