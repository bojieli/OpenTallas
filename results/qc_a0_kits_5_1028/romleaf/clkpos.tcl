read_db /base/6_final.odb
set blk [ord::get_db_block]
foreach i [$blk getInsts] {
  set n [$i getName]
  if {[regexp {^(clk|delaybuf|clkbuf|u_rom)} $n]} {
    set b [$i getBBox]
    set out ""
    foreach it [$i getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { set out [[$it getNet] getName] } }
    if {[regexp {leaf} $n]} continue
    puts [format "%-26s %-22s %7.2f %7.2f %s" $n [[$i getMaster] getName] [expr [$b xMin]/1000.0] [expr [$b yMin]/1000.0] $out]
  }
}
foreach nn {clk clknet_0_clk_regs clk_regs} { set net [$blk findNet $nn]; if {$net ne "NULL"} { set w [$net getWire]; puts "net $nn wire [expr {$w eq \"NULL\" ? 0 : [$w getLength]/1000.0}]" } }
