read_db /work/clock_installed.odb
set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
set count 0;set over 0;set worst 0;set arg {};set f [open /work/macro_interface_edges.tsv w]
puts $f "distance_um\tdriver\tsink\tnet"
proc point_of {it} {set v [$it getAvgXY];if {[llength $v]==3} {lassign $v ok x y;if {!$ok} {error "NO_DATA_PIN_GEOMETRY"}} else {lassign $v x y};return [list $x $y]}
foreach n [$b getNets] {
 if {[$n getSigType] in {CLOCK POWER GROUND}} {continue}
 set terms [$n getITerms];set has 0
 foreach it $terms {if {[[[$it getInst] getMaster] isBlock]} {set has 1;break}}
 if {!$has} {continue}
 set drivers {};set sinks {}
 foreach it $terms {
  if {[[$it getMTerm] getName] in {clk CLK CK}} {continue}
  if {[$it isOutputSignal]} {lappend drivers $it} elseif {[$it isInputSignal]} {lappend sinks $it}
 }
 foreach d $drivers {
  set di [$d getInst];set dm [[$di getMaster] isBlock];lassign [point_of $d] dx dy
  foreach s $sinks {
   set si [$s getInst];if {!$dm && ![[ $si getMaster] isBlock]} {continue}
   lassign [point_of $s] sx sy;set dist [expr {(abs($sx-$dx)+abs($sy-$dy))/$u}]
   set dn "[$di getName]/[[$d getMTerm] getName]";set sn "[$si getName]/[[$s getMTerm] getName]"
   puts $f "$dist\t$dn\t$sn\t[$n getName]";incr count
   if {$dist>405.0} {incr over}
   if {$dist>$worst} {set worst $dist;set arg [list $dn $sn]}
  }
 }
}
close $f
puts "A0_MACRO_INTERFACE_DIRECT_REACH edges=$count max_um=$worst over405=$over worst=$arg"
