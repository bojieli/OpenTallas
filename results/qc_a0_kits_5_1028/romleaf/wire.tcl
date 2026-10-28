read_db /base/6_final.odb
set blk [ord::get_db_block]
foreach nn {clk clk_tb0_tree clk_regs clknet_0_clk_regs delaynet_0_clk delaynet_1_clk delaynet_2_clk} {
  set net [$blk findNet $nn]
  if {$net eq "NULL"} {puts "$nn none"; continue}
  set w [$net getWire]
  set L -1
  if {$w ne "NULL"} { set L [$w getLength] }

  puts "WIRE $nn len $L terms [$net getITermCount]"
}
