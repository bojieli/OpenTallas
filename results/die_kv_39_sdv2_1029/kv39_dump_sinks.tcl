read_db /work/run/results/asap7/dp_kv3_sys_SD/base/3_place.odb
set blk [ord::get_db_block]
set fh [open /work/kv39_sinks.txt w]
foreach i [$blk getInsts] {
  set m [[$i getMaster] getName]
  set b [$i getBBox]
  set cx [expr {([$b xMin]+[$b xMax])/2000.0}]; set cy [expr {([$b yMin]+[$b yMax])/2000.0}]
  if {[[$i getMaster] isBlock]} { puts $fh "MACRO [$i getName] $m [expr {[$b xMin]/1000.0}] [expr {[$b yMin]/1000.0}] [expr {[$b xMax]/1000.0}] [expr {[$b yMax]/1000.0}]"; 
     foreach it [$i getITerms] { set mt [$it getMTerm]; if {[$mt getSigType] eq "CLOCK" || [string match -nocase *clk* [$mt getName]]} { set n [$it getNet]; puts $fh "MPIN [$i getName] [$mt getName] [expr {$n eq "NULL" ? "-" : [$n getName]}]" } }
     continue }
  if {![string match *DFF* $m] && ![string match *DHL* $m] && ![string match *DLL* $m] && ![string match *ICG* $m] && ![string match *SDF* $m]} continue
  set it [$i findITerm CLK]; if {$it eq "NULL"} { set it [$i findITerm CK] }
  set n "-"; if {$it ne "NULL" && [$it getNet] ne "NULL"} { set n [[$it getNet] getName] }
  puts $fh "FF [$i getName] $m $cx $cy $n"
}
foreach bt [$blk getBTerms] { set n [$bt getName]; if {[regexp {^(clk|fclk|clk_)} $n]} { set bb [$bt getBBox]; puts $fh "PORT $n [expr {([$bb xMin]+[$bb xMax])/2000.0}] [expr {([$bb yMin]+[$bb yMax])/2000.0}]" } }
close $fh
