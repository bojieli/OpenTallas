read_db /work/results/asap7/opentallas_dsfd_ctrl_rg2_asap7_ref_gate/base/3_place.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /model/instances.tsv w]; puts $f "name\tmaster\tblock\tstatus\tx\ty\tw\th\tarea"
foreach i [$b getInsts] {set m [$i getMaster];set r [$i getBBox];set x [expr {[$r xMin]/double($dbu)}];set y [expr {[$r yMin]/double($dbu)}];set w [expr {[expr {[$r xMax]-[$r xMin]}]/double($dbu)}];set h [expr {[expr {[$r yMax]-[$r yMin]}]/double($dbu)}];puts $f "[$i getName]\t[$m getName]\t[$m isBlock]\t[$i getPlacementStatus]\t$x\t$y\t$w\t$h\t[expr {$w*$h}]"}
close $f
puts "CTRL_BANK64_ACTUAL_INSTANCES [llength [$b getInsts]]"

set f [open /model/driver_reach.tsv w];puts $f "net\ttype\tendpoint\tio\txlo\tylo\txhi\tyhi"
set roles [open /model/register_pins.tsv w];puts $roles "role\tpin"
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND}} continue
 foreach it [$net getITerms] {
  set box [$it getBBox];set inst [$it getInst];set master [$inst getMaster];set mn [$master getName];set pn [[$it getMTerm] getName];set ep "[$inst getName]/$pn";set ty [$it getIoType]
  puts $f "[$net getName]\t[$net getSigType]\t$ep\t$ty\t[expr {[$box xMin]/double($dbu)}]\t[expr {[$box yMin]/double($dbu)}]\t[expr {[$box xMax]/double($dbu)}]\t[expr {[$box yMax]/double($dbu)}]"
  if {[string match DFF* $mn]} {if {$ty eq "OUTPUT"} {puts $roles "output\t$ep"} elseif {$pn in {CLK CK CP}} {puts $roles "clock\t$ep"} elseif {$pn in {RESETN SETN}} {puts $roles "async\t$ep"} else {puts $roles "data\t$ep"}}
  if {[$master isBlock]} {if {$pn in {rclk wclk}} {puts $roles "clock\t$ep"} elseif {$ty eq "OUTPUT"} {puts $roles "macro_output\t$ep"} else {puts $roles "macro_data\t$ep"}}
 }
 foreach bt [$net getBTerms] {foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts $f "[$net getName]\t[$net getSigType]\tPORT/[$bt getName]\tPORT_[$bt getIoType]\t[expr {[$box xMin]/double($dbu)}]\t[expr {[$box yMin]/double($dbu)}]\t[expr {[$box xMax]/double($dbu)}]\t[expr {[$box yMax]/double($dbu)}]"}}}
}
close $f;close $roles
