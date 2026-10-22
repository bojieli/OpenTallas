read_db /input/3_place.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
puts "BOUNDARY_INSPECT db_units=$u"
foreach name {{xb_d7[230]} {xb_d5[160]} {xb_d0[0]}} {
 set bt [$b findBTerm $name]
 set n [$bt getNet]
 puts "PORT $name net=[$n getName]"
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts "PIN_RECT [$box xMin],[$box yMin],[$box xMax],[$box yMax]"}}
 foreach it [$n getITerms] {
  set i [$it getInst]
  puts "CONNECTED [$i getName]/[[$it getMTerm] getName] master=[[$i getMaster] getName] xy=[$i getLocation] bbox=[[$i getBBox] xMin],[[$i getBBox] yMin],[[$i getBBox] xMax],[[$i getBBox] yMax]"
 }
}
foreach i [$b getInsts] {set name [$i getName]; if {[string match {*xb_d7*230*} $name] || $name eq "wire13703"} {puts "OUTPUT_REG $name master=[[$i getMaster] getName] xy=[$i getLocation]"}}
exit
