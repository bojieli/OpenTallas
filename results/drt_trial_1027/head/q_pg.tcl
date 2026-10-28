read_db /work/run/results/asap7/dp_hd_tile/base/5_2_route.odb
set b [ord::get_db_block]
foreach nn {VDD VSS} {
 set n [$b findNet $nn]
 set ys {}
 foreach sw [$n getSWires] { foreach s [$sw getWires] { if {[$s isVia]} continue; set l [[$s getTechLayer] getName]; if {$l ne "M6"} continue; if {[$s xMin] < 177000 && [$s xMax] > 177300} { lappend ys [list [expr {[$s yMin]/1000.0}] [expr {[$s yMax]/1000.0}]] } } }
 set ys [lsort -real -index 0 $ys]
 puts "$nn M6 straps over x=177.2: [llength $ys] first [lrange $ys 0 3] near170 [lsearch -all -inline -real -index 0 $ys 17*]"
}
foreach i [$b getInsts] { if {[string match *u_eA0 [$i getName]]} { foreach it [$i getITerms] { set m [$it getMTerm]; if {[$m getName] in {rst_n clk}} { set bb [$it getBBox]; puts "eA0 [$m getName] pin bbox [expr {[$bb xMin]/1000.0}] [expr {[$bb yMin]/1000.0}] [expr {[$bb xMax]/1000.0}] [expr {[$bb yMax]/1000.0}] net [[$it getNet] getName]" } } } }
