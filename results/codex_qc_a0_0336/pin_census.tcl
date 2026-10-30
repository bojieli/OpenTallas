read_db /work/diag/cts_prehold.odb
set b [ord::get_db_block]
set f [open /out/macro_data_edges.tsv w]
puts $f "net\tinst0\tx0\ty0\tinst1\tx1\ty1"
set printed 0
foreach net [$b getNets] {
 if {[$net getSigType] in {CLOCK POWER GROUND}} continue
 set terms [$net getITerms]
 set has 0
 foreach it $terms {if {[string match *u_native_rawleaf [[$it getInst] getName]]} {set has 1;break}}
 if {!$has} continue
 set drivers {};set sinks {}
 foreach it $terms {
  set v [$it getAvgXY]
  if {[llength $v]==3} {lassign $v ok x y} elseif {[llength $v]==2} {lassign $v x y} else {error "UNEXPECTED_AVGXY $v"}
  set t [list [[$it getInst] getName] $x $y]
  if {[$it getIoType] eq "OUTPUT"} {lappend drivers $t} elseif {[$it getIoType] eq "INPUT"} {lappend sinks $t}
 }
 foreach a $drivers {foreach z $sinks {
  lassign $a ai ax ay;lassign $z zi zx zy
  puts $f "[$net getName]\t$ai\t$ax\t$ay\t$zi\t$zx\t$zy"
 }}
}
close $f
