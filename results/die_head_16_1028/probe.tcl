read_db /work/run/results/asap7/dp_hd_tile/base/3_place.odb
set b [ord::get_db_block]
foreach o [$b getBlockages] { set r [$o getBBox]; puts "BLK [expr [$r xMin]/1000.0] [expr [$r yMin]/1000.0] [expr [$r xMax]/1000.0] [expr [$r yMax]/1000.0]" }
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { set r [$i getBBox]; puts "MAC [$i getName] [expr [$r xMin]/1000.0] [expr [$r yMin]/1000.0] [expr [$r xMax]/1000.0] [expr [$r yMax]/1000.0]" } }
foreach t {clk fclk_in_i fclk_out_o} { set bt [$b findBTerm $t]; if {$bt eq "NULL"} continue; set bb [$bt getBBox]; puts "PORT $t [expr [$bb xMin]/1000.0] [expr [$bb yMin]/1000.0] net [[$bt getNet] getName]" }
set fh [open /out/sinks.txt w]
foreach t {clk fclk_in_i} { set n [[$b findBTerm $t] getNet]
 foreach it [$n getITerms] { set i [$it getInst]; set r [$i getBBox]; puts $fh "$t [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName] [expr ([$r xMin]+[$r xMax])/2000.0] [expr ([$r yMin]+[$r yMax])/2000.0] [$i getPlacementStatus]" } }
close $fh
